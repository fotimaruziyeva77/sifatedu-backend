"""Kunlik test: offlayn guruh, 3 o'quvchi; 2 dars o'tilgan (har birida 12 savol), uchinchisi —
yo'q (uning savollari testga tushmasligi kerak)."""

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import GroupLesson
from apps.quizzes.models import Choice, Question, Quiz
from apps.users.models import User
from apps.users.roles import Role, set_roles

DAY = date(2026, 10, 5)  # dushanba


@dataclass
class World:
    course: Course
    lessons: list[Lesson]
    group: StudyGroup
    teacher: User
    students: list[User]
    hidden: set[int]  # o'tilmagan dars savollari


def at(hour: int, minute: int = 0, day: date = DAY) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def make_user(phone: str, *roles: str, name: str = "Aziz", last: str = "") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name, last_name=last)
    if roles:
        set_roles(user, roles)
    return user


def bank(lesson: Lesson, count: int) -> list[int]:
    """Bitta to'g'ri javobli savollar: "2+n?" → to'g'risi "2+n"."""
    quiz = Quiz.objects.create(lesson=lesson, title=f"{lesson.title} testi")
    ids = []
    for number in range(count):
        question = Question.objects.create(quiz=quiz, text=f"{lesson.pk}: 2+{number}?")
        Choice.objects.create(question=question, text=str(2 + number), is_correct=True)
        Choice.objects.create(question=question, text=str(3 + number))
        ids.append(question.pk)
    return ids


def api(user: User | None = None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


@pytest.fixture(autouse=True)
def _clean_cache() -> Any:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def world(db: Any) -> World:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="python", title_uz="Python", category=category)
    module = Module.objects.create(course=course, title_uz="Asoslar")
    lessons = [
        Lesson.objects.create(module=module, title_uz=f"Dars {number}", order=number)
        for number in range(1, 4)
    ]
    teacher = make_user("+998901000001", Role.TEACHER, name="Ustoz")
    group = StudyGroup.objects.create(
        course=course,
        teacher=teacher,
        name="Python-1",
        study_format="OFFLINE",
        status=StudyGroup.Status.ACTIVE,
    )
    students = [
        make_user("+998901000011", Role.STUDENT, name="Ali", last="Valiyev"),
        make_user("+998901000012", Role.STUDENT, name="Bekzod", last="Karimov"),
        make_user("+998901000013", Role.STUDENT, name="Dilnoza", last="Saidova"),
    ]
    for student in students:
        Enrollment.objects.create(user=student, course=course, group=group)
    for lesson in lessons[:2]:
        bank(lesson, 12)
        GroupLesson.objects.create(group=group, lesson=lesson, opened_by=teacher)
    hidden = set(bank(lessons[2], 12))
    return World(course, lessons, group, teacher, students, hidden)
