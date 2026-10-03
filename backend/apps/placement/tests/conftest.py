"""Daraja testi: «Python» yo'nalishi, savollar — xizmat kursidagi dars testida (5 turdagi savol)."""

from dataclasses import dataclass
from typing import Any

import pytest
from django.core.cache import cache

from apps.catalog.models import Category, Course, Lesson, Module
from apps.placement.models import PlacementTest
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.quizzes.tests.conftest import SOURCE
from apps.users.models import User


@dataclass
class World:
    course: Course
    quiz: Quiz
    test: PlacementTest
    user: User


def make_user(phone: str, *, source: str = "") -> User:
    return User.objects.create_user(
        phone=phone, password="x", first_name="Aziz", last_name="Valiyev", signup_source=source
    )


@pytest.fixture(autouse=True)
def _clean_cache() -> Any:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def world(db: Any) -> World:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(
        slug="python",
        title_uz="Python",
        category=category,
        status=Course.Status.PUBLISHED,
        price_online=1_000_000,
    )
    service = Course.objects.create(
        slug="daraja-testlari", title_uz="Daraja testlari", category=category
    )
    module = Module.objects.create(course=service, title_uz="Python")
    lesson = Lesson.objects.create(module=module, title_uz="Python: daraja testi")
    quiz = Quiz.objects.create(lesson=lesson, title="Python: daraja testi")
    import_questions(quiz, parse(SOURCE))
    test = PlacementTest.objects.create(
        course=course, title="Python", quiz=quiz, questions_count=5, duration_min=15
    )
    return World(course, quiz, test, make_user("+998901234567", source="ig"))
