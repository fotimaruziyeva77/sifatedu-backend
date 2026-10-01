from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, Module
from apps.exams.models import Exam, ExamTask
from apps.exams.services import month_start
from apps.learning.models import Enrollment, StudyGroup
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.users.models import User
from apps.users.roles import Role, set_roles

SOURCE = """
? HTML nimaning qisqartmasi?
+ HyperText Markup Language
- High Tech Modern Language

? Qaysilari HTML teglari?
+ <div>
+ <p>
- <color>

? Eng katta sarlavha tegi qaysi?
= h1

? CSS nima uchun?
+ Ko'rinish
- Ma'lumotlar bazasi

? JavaScript qayerda ishlaydi?
+ Brauzerda
- Faqat printerda
"""


@dataclass
class World:
    course: Course
    lessons: list[Lesson]
    quiz: Quiz
    exam: Exam
    tasks: list[ExamTask]
    student: User
    teacher: User
    group: StudyGroup


def make_user(phone: str, *roles: str, name: str = "Aziz") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name, last_name="Valiyev")
    if roles:
        set_roles(user, roles)
    return user


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
    """Onlayn guruh, 2 dars (birinchisida 5 savolli test), ochiq imtihon (4 savol, 2 topshiriq)."""
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(
        slug="frontend", title_uz="Frontend", category=category, status=Course.Status.PUBLISHED
    )
    module = Module.objects.create(course=course, title_uz="HTML")
    lessons = [
        Lesson.objects.create(module=module, title_uz=f"Dars {index}", order=index)
        for index in range(1, 3)
    ]
    quiz = Quiz.objects.create(lesson=lessons[0], title="HTML")
    import_questions(quiz, parse(SOURCE))
    student = make_user("+998901000001", Role.STUDENT)
    teacher = make_user("+998901000002", Role.TEACHER, name="Ustoz")
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="FE-1", study_format="ONLINE"
    )
    Enrollment.objects.create(user=student, course=course, group=group)
    now = timezone.now()
    exam = Exam.objects.create(
        course=course,
        month=month_start(timezone.localdate()),
        status=Exam.Status.READY,
        questions_count=4,
        duration_min=40,
        opens_at=now - timedelta(hours=1),
        closes_at=now + timedelta(days=2),
    )
    tasks = [
        ExamTask.objects.create(
            exam=exam, order=index, title=f"Topshiriq {index}", instructions="Sahifa"
        )
        for index in (1, 2)
    ]
    return World(course, lessons, quiz, exam, tasks, student, teacher, group)
