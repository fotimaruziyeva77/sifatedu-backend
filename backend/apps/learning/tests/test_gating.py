"""Onlayn o'quvchi: keyingi dars oldingi darsning testidan o'tilgach ochiladi."""

from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning import access
from apps.learning.models import Enrollment, LessonProgress, StudyGroup
from apps.quizzes.models import Attempt, Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db


@pytest.fixture
def lessons(db: Any) -> list[Lesson]:
    """1-dars testli, 3-dars bepul (preview), 2 va 4 — oddiy."""
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="frontend", title_uz="Frontend", category=category)
    module = Module.objects.create(course=course, title_uz="HTML")
    items = [
        Lesson.objects.create(
            module=module, title_uz=f"Dars {index}", order=index, is_preview=index == 3
        )
        for index in range(1, 5)
    ]
    quiz = Quiz.objects.create(lesson=items[0], title="HTML")
    import_questions(quiz, parse("? HTML nima?\n+ Belgilash tili\n- Dastur\n"))
    return items


@pytest.fixture
def student(lessons: list[Lesson]) -> User:
    user = User.objects.create_user(phone="+998901112233", password="x")
    Enrollment.objects.create(user=user, course=lessons[0].module.course)
    return user


def api(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def program(user: User) -> list[dict[str, Any]]:
    body = api(user).get("/api/v1/my/courses/frontend/").json()
    return [lesson for module in body["modules"] for lesson in module["lessons"]]


def pass_quiz(user: User, lesson: Lesson) -> None:
    Attempt.objects.create(
        quiz=lesson.quiz, student=user, passed=True, score=100, finished_at=timezone.now()
    )


def test_lessons_wait_for_the_quiz(student: User, lessons: list[Lesson]) -> None:
    first, second, preview, last = lessons

    rows = program(student)

    assert [(row["locked"], row["lock_reason"], row["blocked_by"]) for row in rows] == [
        (False, None, None),
        (True, "quiz", first.pk),
        (False, None, None),
        (True, "quiz", first.pk),
    ]
    assert api(student).get(f"/api/v1/lessons/{second.pk}/").status_code == 403
    assert api(student).get(f"/api/v1/lessons/{preview.pk}/").status_code == 200
    assert access.lesson_lock(student, last) == (access.LOCK_QUIZ, first.pk)

    pass_quiz(student, first)

    assert not any(row["locked"] for row in program(student))
    assert api(student).get(f"/api/v1/lessons/{second.pk}/").status_code == 200


def test_continue_button_leads_to_the_unpassed_quiz(student: User, lessons: list[Lesson]) -> None:
    first, second, *_rest = lessons
    # Video ko'rilgan (dars tugatilgan), lekin test hali o'tilmagan.
    LessonProgress.objects.create(user=student, lesson=first, completed_at=timezone.now())

    [card] = api(student).get("/api/v1/my/courses/").json()
    assert card["next_lesson_id"] == first.pk

    pass_quiz(student, first)
    [card] = api(student).get("/api/v1/my/courses/").json()
    assert card["next_lesson_id"] == second.pk


def test_offline_group_and_staff_are_not_gated(student: User, lessons: list[Lesson]) -> None:
    course = lessons[0].module.course
    teacher = User.objects.create_user(phone="+998901112244", password="x")
    set_roles(teacher, [Role.TEACHER])
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="FE-1", study_format="OFFLINE"
    )
    Enrollment.objects.filter(user=student).update(group=group)

    assert access.quiz_gate(student, course.pk) == {}
    assert access.can_open_lesson(teacher, lessons[1])


def test_quiz_without_questions_does_not_block(student: User, lessons: list[Lesson]) -> None:
    lessons[0].quiz.questions.all().delete()

    assert access.quiz_gate(student, lessons[0].module.course_id) == {}
