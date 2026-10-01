"""«O'qishga qaytish» eslatmalari: 3 va 7 kunlik tanaffus, takrorlanmaydi, keraksizlarga yo'q."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning.models import Enrollment, LessonProgress
from apps.notifications.models import Notification
from apps.notifications.tasks import remind_inactive
from apps.quizzes.models import Attempt, Quiz
from apps.users.models import User

from .conftest import make_student

pytestmark = pytest.mark.django_db


@pytest.fixture
def lessons(db: Any) -> list[Lesson]:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="frontend", title_uz="Frontend", category=category)
    module = Module.objects.create(course=course, title_uz="HTML")
    return [
        Lesson.objects.create(module=module, title_uz=f"Dars {index}", order=index)
        for index in range(1, 4)
    ]


@pytest.fixture
def student(lessons: list[Lesson]) -> User:
    user = make_student()
    Enrollment.objects.create(user=user, course=lessons[0].module.course)
    return user


def studied(user: User, lesson: Lesson, days: int, *, completed: bool = True) -> None:
    moment = timezone.now() - timedelta(days=days)
    progress = LessonProgress.objects.create(
        user=user, lesson=lesson, completed_at=moment if completed else None
    )
    LessonProgress.objects.filter(pk=progress.pk).update(updated_at=moment)


def reminders() -> list[Notification]:
    return list(Notification.objects.filter(kind=Notification.Kind.INACTIVE).order_by("pk"))


@pytest.mark.parametrize(
    ("days", "title"),
    [(1, None), (3, "Darsni davom ettiramizmi?"), (7, "Sizni kutyapmiz"), (20, None)],
)
def test_break_length_picks_the_reminder(
    student: User, lessons: list[Lesson], days: int, title: str | None
) -> None:
    studied(student, lessons[0], days)

    remind_inactive()

    found = reminders()
    assert [note.title for note in found] == ([title] if title else [])
    if found:
        assert found[0].user == student
        assert found[0].link == f"/dashboard/courses/frontend/lessons/{lessons[1].pk}"
        assert "«Dars 2»" in found[0].body


def test_each_step_is_sent_once_per_break(student: User, lessons: list[Lesson]) -> None:
    studied(student, lessons[0], 3)

    remind_inactive()
    remind_inactive()
    LessonProgress.objects.update(updated_at=timezone.now() - timedelta(days=7))
    remind_inactive()

    assert [note.title for note in reminders()] == ["Darsni davom ettiramizmi?", "Sizni kutyapmiz"]


def test_latest_activity_counts_quizzes_too(student: User, lessons: list[Lesson]) -> None:
    studied(student, lessons[0], 5)
    quiz = Quiz.objects.create(lesson=lessons[1])
    attempt = Attempt.objects.create(quiz=quiz, student=student)
    Attempt.objects.filter(pk=attempt.pk).update(started_at=timezone.now() - timedelta(days=1))

    remind_inactive()

    assert reminders() == []


def test_not_started_finished_and_closed_courses_are_skipped(lessons: list[Lesson]) -> None:
    course = lessons[0].module.course
    idle = make_student("+998901000011")
    Enrollment.objects.create(user=idle, course=course)
    graduate = make_student("+998901000012")
    Enrollment.objects.create(user=graduate, course=course)
    for lesson in lessons:
        studied(graduate, lesson, 3)
    expired = make_student("+998901000013")
    Enrollment.objects.create(
        user=expired, course=course, expires_at=timezone.now() - timedelta(days=1)
    )
    studied(expired, lessons[0], 3)

    remind_inactive()

    assert reminders() == []


def test_reminder_is_in_the_students_language(lessons: list[Lesson]) -> None:
    user = make_student("+998901000014", locale="ru")
    Enrollment.objects.create(user=user, course=lessons[0].module.course)
    studied(user, lessons[0], 3, completed=False)

    remind_inactive()

    [note] = reminders()
    assert note.title == "Продолжим обучение?"
    # Boshlangan, lekin tugatilmagan dars — keyingi dars shuning o'zi.
    assert note.link.endswith(f"/lessons/{lessons[0].pk}")
