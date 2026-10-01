"""Sertifikat shartlari, avtomatik berish va tekshirish.

Shartlar (kursda "Sertifikat beriladi" yoqilgan bo'lsa): barcha darslar tugatilgan (offlayn
guruhda — guruhda o'tilgan), testli darslarning testi o'tilgan, uy vazifalari qabul qilingan,
oylik imtihonlar o'rtachasi o'tish balidan yuqori (imtihon bo'lmagan bo'lsa — bu shart yo'q).
"""

import secrets
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Count, Max
from django.utils import timezone, translation

from apps.catalog.models import Course, Lesson
from apps.exams.models import ExamResult
from apps.homework.models import Assignment, Submission
from apps.learning.models import Enrollment, LessonProgress
from apps.live.gates import closed_lessons, offline_group
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import locale_of, text
from apps.quizzes.models import Attempt, Quiz
from apps.users.models import User

from .models import Certificate

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
EXAM_PASS = 60


@dataclass(frozen=True)
class Requirement:
    """Shart: `lessons`, `quizzes`, `homework` — bajarilgani / jami;
    `exams` — o'rtacha foiz / kerakli foiz."""

    code: str
    done: int
    total: int

    @property
    def ok(self) -> bool:
        return self.done >= self.total


def course_quizzes(course: Course) -> dict[int, int]:
    """Savoli bor testlar: quiz → dars."""
    return dict(
        Quiz.objects.filter(lesson__module__course=course)
        .annotate(count=Count("questions"))
        .filter(count__gt=0)
        .values_list("pk", "lesson_id")
    )


def requirements(user: User, course: Course) -> list[Requirement]:
    lessons = list(Lesson.objects.filter(module__course=course).values_list("pk", flat=True))
    if offline_group(user, course.pk) is not None:
        waiting = closed_lessons(user, course.pk)
        lessons_done = sum(1 for lesson in lessons if lesson not in waiting)
    else:
        completed = set(
            LessonProgress.objects.filter(
                user=user, lesson__module__course=course, completed_at__isnull=False
            ).values_list("lesson_id", flat=True)
        )
        lessons_done = sum(1 for lesson in lessons if lesson in completed)
    quizzes = course_quizzes(course)
    passed = set(
        Attempt.objects.filter(student=user, quiz_id__in=quizzes, passed=True).values_list(
            "quiz_id", flat=True
        )
    )
    assignments = set(
        Assignment.objects.filter(lesson__module__course=course).values_list("pk", flat=True)
    )
    accepted = set(
        Submission.objects.filter(
            student=user, assignment_id__in=assignments, status=Submission.Status.ACCEPTED
        ).values_list("assignment_id", flat=True)
    )
    items = [
        Requirement("lessons", lessons_done, len(lessons)),
        Requirement("quizzes", len(passed), len(quizzes)),
        Requirement("homework", len(accepted), len(assignments)),
    ]
    exams = exam_totals(user, course)
    if exams:
        items.append(Requirement("exams", round(mean(exams)), EXAM_PASS))
    return items


def exam_totals(user: User, course: Course) -> list[int]:
    return list(
        ExamResult.objects.filter(
            student=user, exam__course=course, final_at__isnull=False
        ).values_list("total", flat=True)
    )


def score(user: User, course: Course) -> int:
    """Umumiy ball: testlar (eng yaxshi natija), uy vazifalari va imtihonlar o'rtachasi."""
    parts: list[float] = []
    quizzes = course_quizzes(course)
    best = [
        row["best"] or 0
        for row in Attempt.objects.filter(
            student=user, quiz_id__in=quizzes, finished_at__isnull=False
        )
        .values("quiz_id")
        .annotate(best=Max("score"))
    ]
    if best:
        parts.append(mean(best))
    homework = [
        value
        for value in Submission.objects.filter(
            student=user,
            assignment__lesson__module__course=course,
            status=Submission.Status.ACCEPTED,
        ).values_list("score", flat=True)
        if value is not None
    ]
    if homework:
        parts.append(mean(homework))
    exams = exam_totals(user, course)
    if exams:
        parts.append(mean(exams))
    return round(mean(parts)) if parts else 100


def new_number(now: datetime) -> str:
    return f"SE-{now:%y%m}-" + "".join(secrets.choice(ALPHABET) for _ in range(6))


def issue(user: User, course: Course, *, now: datetime | None = None) -> Certificate:
    now = now or timezone.now()
    name = user.get_full_name() or user.first_name or user.phone
    for _attempt in range(5):
        try:
            with transaction.atomic():
                return Certificate.objects.create(
                    user=user,
                    course=course,
                    number=new_number(now),
                    full_name=name[:300],
                    score=score(user, course),
                )
        except IntegrityError:
            existing = Certificate.objects.filter(user=user, course=course).first()
            if existing is not None:  # parallel tekshiruv allaqachon bergan
                return existing
    raise RuntimeError("Sertifikat raqamini yaratib bo'lmadi")


def check(user_id: int, course_id: int) -> Certificate | None:
    """Shartlar bajarilgan bo'lsa — sertifikat beradi va xabar yuboradi. Allaqachon bor (yoki
    bekor qilingan) bo'lsa — hech narsa qilmaydi."""
    course = Course.objects.filter(pk=course_id, certificate=True).first()
    user = User.objects.filter(pk=user_id, is_active=True, is_staff=False).first()
    if course is None or user is None:
        return None
    if Certificate.objects.filter(user=user, course=course).exists():
        return None
    if not Enrollment.objects.filter(
        user=user, course=course, status=Enrollment.Status.ACTIVE
    ).exists():
        return None
    items = requirements(user, course)
    if not items[0].total or not all(item.ok for item in items):
        return None
    certificate = issue(user, course)
    locale = locale_of(user.locale)
    with translation.override(locale):
        title = str(course.title)
    notify(
        user,
        Notification.Kind.CERTIFICATE,
        title=text(locale, "certificate_title", course=title),
        body=text(locale, "certificate_body", number=certificate.number),
        link="/dashboard/certificates",
        dedupe_key=f"certificate:{certificate.pk}",
    )
    return certificate


def schedule(user_id: int, course_id: int) -> None:
    """Hodisadan keyin tekshiruv — tranzaksiya yopilgach, fonda."""
    from .tasks import check_certificate

    transaction.on_commit(lambda: check_certificate.delay(user_id, course_id))


def payload(certificate: Certificate, locale: str) -> dict[str, Any]:
    with translation.override(locale):
        course = str(certificate.course.title)
    return {
        "number": certificate.number,
        "full_name": certificate.full_name,
        "course_title": course,
        "course_slug": certificate.course.slug,
        "score": certificate.score,
        "issued_at": certificate.issued_at,
        "valid": certificate.is_valid,
        "revoked_at": certificate.revoked_at,
        "revoke_reason": certificate.revoke_reason,
    }
