"""Darsga kirish huquqi. Bu qoida bitta joyda: barcha endpointlar shuni ishlatadi.

Onlayn o'quvchida keyingi dars oldingi testli darslarning testi o'tilgach ochiladi (`quiz_gate`).
Bepul (preview) darslar, xodimlar va o'qituvchi ochadigan guruh (offlayn yoki «darslarni o'qituvchi
ochadi» yoqilgan onlayn) o'quvchilari bundan mustasno — ularda darslarni ustoz "Dars o'tildi" bilan
ochadi (apps/live/gates.py).
"""

from typing import Any

from django.db.models import Count, QuerySet

from apps.catalog.models import Course, Lesson
from apps.users.models import User

from .models import Enrollment

# Nega dars yopiq: kursga huquq yo'q yoki oldingi darsning testidan o'tilmagan.
LOCK_ACCESS = "access"
LOCK_QUIZ = "quiz"


def student(user: Any) -> User | None:
    """Kirgan foydalanuvchi bo'lsa qaytaradi. Anonim va AnonymousUser uchun `None`."""
    return user if isinstance(user, User) and user.is_authenticated else None


def open_enrollment(user: Any, course: Course) -> Enrollment | None:
    """Kursga faol yozilish (muddati o'tmagan) bo'lsa qaytaradi."""
    person = student(user)
    if person is None:
        return None
    for enrollment in Enrollment.objects.filter(
        user=person, course=course, status=Enrollment.Status.ACTIVE
    ):
        if enrollment.is_open:
            return enrollment
    return None


def can_open_course(user: Any, course: Course) -> bool:
    """Kurs materiallariga kirish: xodim, bepul kurs yoki faol yozilish."""
    if getattr(user, "is_staff", False):
        return True
    if student(user) is None:
        return False
    if course.is_free:
        return True
    return open_enrollment(user, course) is not None


def quiz_gate(user: Any, course_id: int) -> dict[int, int]:
    """Onlayn o'quvchi uchun testdan o'tmaguncha yopiq darslar: {yopiq dars: to'sib turgan dars}.

    To'sib turgan dars — kurs tartibida testi (kamida bitta savol bilan) hali o'tilmagan birinchi
    dars; undan keyingi barcha darslar (preview'dan tashqari) yopiq.
    """
    from apps.live.gates import paced_group
    from apps.quizzes.models import Attempt, Quiz

    person = student(user)
    if person is None or person.is_staff or paced_group(person, course_id) is not None:
        return {}
    quizzes = dict(
        Quiz.objects.filter(lesson__module__course_id=course_id)
        .annotate(count=Count("questions"))
        .filter(count__gt=0)
        .values_list("lesson_id", "pk")
    )
    if not quizzes:
        return {}
    passed = set(
        Attempt.objects.filter(
            student=person, quiz_id__in=quizzes.values(), passed=True
        ).values_list("quiz_id", flat=True)
    )
    lessons = Lesson.objects.filter(module__course_id=course_id).order_by(
        "module__order", "module__id", "order", "id"
    )
    blocker: int | None = None
    locked: dict[int, int] = {}
    for lesson_id, is_preview in lessons.values_list("id", "is_preview"):
        if blocker is not None:
            if not is_preview:
                locked[lesson_id] = blocker
            continue
        quiz_id = quizzes.get(lesson_id)
        if quiz_id is not None and quiz_id not in passed:
            blocker = lesson_id
    return locked


def lesson_lock(user: Any, lesson: Lesson) -> tuple[str, int | None] | None:
    """Dars yopiq bo'lsa — sababi va (test sababli bo'lsa) to'sib turgan dars. Ochiq — None."""
    if lesson.is_preview:
        return None
    if not can_open_course(user, lesson.module.course):
        return LOCK_ACCESS, None
    blocker = quiz_gate(user, lesson.module.course_id).get(lesson.pk)
    return (LOCK_QUIZ, blocker) if blocker is not None else None


def can_open_lesson(user: Any, lesson: Lesson) -> bool:
    """Bepul (preview) dars hammaga ochiq, qolganiga kurs huquqi va (onlayn o'quvchida)
    oldingi testlardan o'tgan bo'lish kerak."""
    return lesson_lock(user, lesson) is None


def enrolled_courses(user: Any) -> QuerySet[Course]:
    """Kabinetdagi "mening kurslarim": faol yozilish bor kurslar."""
    person = student(user)
    if person is None:
        return Course.objects.none()
    ids = [
        enrollment.course_id
        for enrollment in Enrollment.objects.filter(
            user=person, status=Enrollment.Status.ACTIVE
        ).only("course_id", "expires_at", "status")
        if enrollment.is_open
    ]
    return Course.objects.filter(id__in=ids)


def ensure_free_enrollment(user: Any, course: Course) -> Enrollment | None:
    """Bepul kursni ochganda yozilish o'zi yaratiladi: progress va kabinet ishlashi uchun."""
    person = student(user)
    if not course.is_free or person is None:
        return None
    enrollment, _created = Enrollment.objects.get_or_create(
        user=person,
        course=course,
        defaults={
            "source": Enrollment.Source.FREE,
            "study_format": Enrollment.Format.ONLINE,
        },
    )
    return enrollment
