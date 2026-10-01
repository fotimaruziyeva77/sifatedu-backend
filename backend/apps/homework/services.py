"""Uy vazifalari: javob yuborish, qaytarib olish, tekshirish va kim nimani ko'rishi."""

from collections.abc import Iterable
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.catalog.models import Course, Lesson
from apps.catalog.scope import teacher_courses
from apps.core import events
from apps.learning.models import Enrollment, LessonProgress
from apps.live.gates import closed_lessons
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import locale_of, text
from apps.users.models import User
from apps.users.roles import Role, has_role
from apps.videos import s3

from .files import CheckedFile
from .models import Assignment, Submission, SubmissionFile

# Javob sahifasida havolalar shuncha amal qiladi (dars materiallari bilan bir xil).
LINK_TTL = settings.HLS_SIGNED_URL_TTL_SEC
PREVIEW_CHARS = 140


class HomeworkError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan sabab bilan (API 400)."""


# --- Kim ko'radi va kim tekshiradi ---


def can_review_all(user: Any) -> bool:
    return has_role(user, Role.ADMIN)


def reviewable(user: Any) -> QuerySet[Submission]:
    """O'qituvchi tekshira oladigan javoblar: o'z kurslari va o'z guruhlari o'quvchilariniki.
    Admin — hammasi."""
    submissions = Submission.objects.select_related(
        "student", "assignment", "assignment__lesson", "assignment__lesson__module__course"
    )
    if can_review_all(user):
        return submissions
    if not has_role(user, Role.TEACHER):
        return submissions.none()
    own_group = Enrollment.objects.filter(
        user=OuterRef("student_id"),
        course=OuterRef("assignment__lesson__module__course_id"),
        group__teacher=user,
    )
    return submissions.filter(
        Q(assignment__lesson__module__course__in=teacher_courses(user).values("pk"))
        | Exists(own_group)
    )


def reviewers_for(submission: Submission) -> list[User]:
    """Javobni kim tekshiradi: guruh ustozi, guruh bo'lmasa — kurs ustozlari."""
    course_id = submission.assignment.lesson.module.course_id
    enrollment = (
        Enrollment.objects.filter(user=submission.student, course_id=course_id)
        .select_related("group__teacher")
        .first()
    )
    teacher = enrollment.group.teacher if enrollment and enrollment.group else None
    if teacher is not None and teacher.is_active:
        return [teacher]
    return list(
        User.objects.filter(
            is_active=True,
            instructor_profile__courses__pk=course_id,
        ).distinct()
    )


def pending_reviews(user: Any) -> int:
    if not (has_role(user, Role.TEACHER) or can_review_all(user)):
        return 0
    return reviewable(user).filter(status=Submission.Status.SUBMITTED).count()


# --- O'quvchi ---


def attempts(assignment: Assignment, student: User) -> QuerySet[Submission]:
    return (
        Submission.objects.filter(assignment=assignment, student=student)
        .select_related("reviewer")
        .prefetch_related("files")
        .order_by("-attempt")
    )


@transaction.atomic
def submit(
    assignment: Assignment,
    student: User,
    *,
    text: str = "",
    code: str = "",
    language: str = "",
    link: str = "",
    files: Iterable[CheckedFile] = (),
) -> Submission:
    """Yangi urinish. Tekshirilayotgani bo'lsa yoki vazifa qabul qilingan bo'lsa — rad etiladi."""
    files = list(files)
    if not (text.strip() or code.strip() or link.strip() or files):
        raise HomeworkError(_("Javob bo'sh: izoh, kod, havola yoki fayl qo'shing."))
    # Bir vaqtda ikki marta bosilsa ham urinish raqami takrorlanmasin.
    Assignment.objects.select_for_update().filter(pk=assignment.pk).first()
    last = attempts(assignment, student).first()
    if last is not None and last.status == Submission.Status.SUBMITTED:
        raise HomeworkError(_("Oldingi javobingiz hali tekshirilmoqda."))
    if last is not None and last.status == Submission.Status.ACCEPTED:
        raise HomeworkError(_("Bu vazifa allaqachon qabul qilingan."))
    now = timezone.now()
    submission = Submission.objects.create(
        assignment=assignment,
        student=student,
        attempt=(last.attempt + 1) if last else 1,
        text=text.strip(),
        code=code.rstrip(),
        language=language.strip()[:20] if code.strip() else "",
        link=link.strip(),
        late=bool(assignment.deadline and now > assignment.deadline),
    )
    for item in files:
        SubmissionFile.objects.create(
            submission=submission,
            file=item.upload,
            name=item.name,
            size=item.size,
            content_type=item.content_type,
            is_image=item.is_image,
        )
    transaction.on_commit(lambda: notify_reviewers(submission.pk))
    lesson = assignment.lesson
    events.homework_submitted.send(
        sender=Submission,
        user_id=student.pk,
        course_id=lesson.module.course_id,
        assignment_id=assignment.pk,
        lesson_id=lesson.pk,
        late=submission.late,
    )
    return submission


def withdraw(submission: Submission) -> None:
    """Tekshirilmagan javobni qaytarib olish (fayllari ham o'chadi)."""
    if submission.status != Submission.Status.SUBMITTED:
        raise HomeworkError(_("Tekshirilgan javobni qaytarib olib bo'lmaydi."))
    submission.delete()


# --- O'qituvchi ---


def review(
    submission: Submission, reviewer: User, *, accept: bool, score: int | None, feedback: str
) -> Submission:
    feedback = feedback.strip()
    if accept and score is None:
        raise HomeworkError(_("Qabul qilish uchun baho qo'ying (0–100)."))
    if not accept and not feedback:
        raise HomeworkError(_("Qaytarishda nimani tuzatish kerakligini yozing."))
    with transaction.atomic():
        locked = Submission.objects.select_for_update().get(pk=submission.pk)
        if locked.status != Submission.Status.SUBMITTED:
            raise HomeworkError(_("Bu javob allaqachon tekshirilgan."))
        locked.status = (
            Submission.Status.ACCEPTED if accept else Submission.Status.CHANGES_REQUESTED
        )
        locked.score = score if accept else None
        locked.feedback = feedback
        locked.reviewer = reviewer
        locked.reviewed_at = timezone.now()
        locked.save(
            update_fields=["status", "score", "feedback", "reviewer", "reviewed_at", "updated_at"]
        )
        transaction.on_commit(lambda: notify_student(locked.pk))
        if accept:
            lesson = locked.assignment.lesson
            events.homework_accepted.send(
                sender=Submission,
                user_id=locked.student_id,
                course_id=lesson.module.course_id,
                assignment_id=locked.assignment_id,
                lesson_id=lesson.pk,
                score=locked.score,
            )
    return locked


# --- Xabarlar ---


def lesson_link(lesson: Lesson) -> str:
    return f"/dashboard/courses/{lesson.module.course.slug}/lessons/{lesson.pk}#homework"


def notify_reviewers(submission_id: int) -> None:
    submission = (
        Submission.objects.select_related("student", "assignment__lesson__module__course")
        .filter(pk=submission_id)
        .first()
    )
    if submission is None:
        return
    lesson = submission.assignment.lesson
    student = submission.student.get_full_name() or submission.student.phone
    for teacher in reviewers_for(submission):
        locale = locale_of(teacher.locale)
        with translation.override(locale):
            course = str(lesson.module.course.title)
            lesson_title = str(lesson.title)
        notify(
            teacher,
            Notification.Kind.HOMEWORK_SUBMITTED,
            title=text(locale, "homework_new_title", student=student),
            body=text(locale, "homework_new_body", course=course, lesson=lesson_title),
            link=f"/dashboard/reviews/{submission.pk}",
            dedupe_key=f"homework:new:{submission.pk}:{teacher.pk}",
        )


def notify_student(submission_id: int) -> None:
    submission = (
        Submission.objects.select_related("student", "assignment__lesson__module__course")
        .filter(pk=submission_id)
        .first()
    )
    if submission is None:
        return
    student = submission.student
    locale = locale_of(student.locale)
    lesson = submission.assignment.lesson
    with translation.override(locale):
        lesson_title = str(lesson.title)
    accepted = submission.status == Submission.Status.ACCEPTED
    key = "homework_accepted_body" if accepted else "homework_returned_body"
    body = text(locale, key, lesson=lesson_title, score=str(submission.score or 0))
    if submission.feedback:
        body += "\n\n" + submission.feedback[:600]
    notify(
        student,
        Notification.Kind.HOMEWORK_REVIEWED,
        title=text(locale, "homework_reviewed_title"),
        body=body,
        link=lesson_link(lesson),
        dedupe_key=f"homework:reviewed:{submission.pk}",
    )


# --- Javob ko'rinishi (API) ---


def file_payload(item: SubmissionFile) -> dict[str, Any]:
    # Rasm sahifada ko'rinsin (inline), qolganlari asl nomi bilan yuklab olinadi.
    url = s3.sign_get(item.file.name, LINK_TTL, download_name=None if item.is_image else item.name)
    return {
        "id": item.pk,
        "name": item.name,
        "size": item.size,
        "is_image": item.is_image,
        "url": url,
    }


def submission_payload(submission: Submission) -> dict[str, Any]:
    reviewer = submission.reviewer
    return {
        "id": submission.pk,
        "attempt": submission.attempt,
        "status": submission.status,
        "text": submission.text,
        "code": submission.code,
        "language": submission.language,
        "link": submission.link,
        "late": submission.late,
        "files": [file_payload(item) for item in submission.files.all()],
        "created_at": submission.created_at,
        "score": submission.score,
        "feedback": submission.feedback,
        "reviewer_name": (reviewer.get_full_name() or reviewer.phone) if reviewer else "",
        "reviewed_at": submission.reviewed_at,
    }


def homework_payload(lesson: Lesson, user: Any) -> dict[str, Any] | None:
    """Dars sahifasi uchun: vazifa va o'quvchining urinishlari (eng yangisi birinchi)."""
    assignment = Assignment.objects.filter(lesson=lesson).first()
    if assignment is None:
        return None
    rows = list(attempts(assignment, user)) if isinstance(user, User) else []
    return {
        "id": assignment.pk,
        "title": assignment.title,
        "instructions": assignment.instructions,
        "deadline": assignment.deadline,
        "status": rows[0].status if rows else "NOT_SUBMITTED",
        "attempts": [submission_payload(row) for row in rows],
    }


def lesson_order(course: Course) -> list[int]:
    return list(
        Lesson.objects.filter(module__course=course)
        .order_by("module__order", "module__id", "order", "id")
        .values_list("id", flat=True)
    )


def my_homework(user: User, courses: QuerySet[Course]) -> list[dict[str, Any]]:
    """ "Vazifalar" sahifasi. Topshirilmaganlar — faqat o'quvchi yetib kelgan darslar bo'yicha
    (oxirgi ko'rgan darsi va keyingisi), yuborilganlari — hammasi."""
    assignments = list(
        Assignment.objects.filter(lesson__module__course__in=courses).select_related(
            "lesson", "lesson__module", "lesson__module__course"
        )
    )
    if not assignments:
        return []
    latest: dict[int, Submission] = {}
    rows = Submission.objects.filter(student=user, assignment__in=assignments)
    for row in rows.order_by("assignment_id", "-attempt"):
        latest.setdefault(row.assignment_id, row)
    seen = set(LessonProgress.objects.filter(user=user).values_list("lesson_id", flat=True))
    reach: dict[int, int] = {}
    positions: dict[int, int] = {}
    # Offlayn guruhda ustoz hali o'tmagan darslarning vazifalari ko'rinmaydi.
    closed: set[int] = set()
    for course in {assignment.lesson.module.course for assignment in assignments}:
        closed |= closed_lessons(user, course)
        order = lesson_order(course)
        positions.update({lesson_id: index for index, lesson_id in enumerate(order)})
        visited = [index for index, lesson_id in enumerate(order) if lesson_id in seen]
        reach[course.pk] = (max(visited) if visited else -1) + 1

    items = []
    for assignment in assignments:
        lesson = assignment.lesson
        course = lesson.module.course
        submission = latest.get(assignment.pk)
        if submission is None and lesson.pk in closed:
            continue
        if submission is None and positions.get(lesson.pk, 0) > reach.get(course.pk, 0):
            continue
        items.append(
            {
                "assignment_id": assignment.pk,
                "title": assignment.title,
                "lesson_id": lesson.pk,
                "lesson_title": lesson.title,
                "course_slug": course.slug,
                "course_title": course.title,
                "deadline": assignment.deadline,
                "status": submission.status if submission else "NOT_SUBMITTED",
                "score": submission.score if submission else None,
                "updated_at": submission.updated_at if submission else None,
                "position": positions.get(lesson.pk, 0),
            }
        )
    return items


def preview(submission: Submission) -> str:
    """Navbatdagi qisqa ko'rinish: izohning boshi yoki nima yuborilgani."""
    source = submission.text or submission.code or submission.link
    return " ".join(source.split())[:PREVIEW_CHARS]
