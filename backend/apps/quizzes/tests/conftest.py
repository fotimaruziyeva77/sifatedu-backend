from dataclasses import dataclass
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Instructor, Lesson, Module
from apps.learning.models import Enrollment, StudyGroup
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.users.models import User
from apps.users.roles import Role, set_roles

# Besh turdagi savol; to'g'ri javoblar quyidagi ANSWERS da (matn bo'yicha — ID larni brauzer
# ko'rmaydi, faqat ekrandagi o'rinlarni).
SOURCE = """
? HTML nimaning qisqartmasi?
+ HyperText Markup Language
- High Tech Modern Language
- Hyper Tool Multi Language
> Izoh: HTML — sahifa tuzilmasi uchun belgilash tili.

? Qaysilari HTML teglari?
+ <div>
+ <p>
- <color>

? Eng katta sarlavha tegi qaysi?
= h1
= <h1>

? Brauzer sahifani qanday tayyorlaydi?
1. HTML o'qiladi
2. CSS qo'llanadi
3. JavaScript ishga tushadi

? Moslang:
HTML :: tuzilma
CSS :: ko'rinish
JavaScript :: harakat
"""
KINDS = ["SINGLE", "MULTIPLE", "TEXT", "ORDER", "MATCH"]
STEPS = ["HTML o'qiladi", "CSS qo'llanadi", "JavaScript ishga tushadi"]
PAIRS = {"HTML": "tuzilma", "CSS": "ko'rinish", "JavaScript": "harakat"}


@dataclass
class World:
    course: Course
    lessons: list[Lesson]
    quiz: Quiz
    student: User
    teacher: User
    group: StudyGroup


def make_user(phone: str, *roles: str, name: str = "") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name or phone[-4:])
    if roles:
        set_roles(user, roles)
    return user


def api(user: User | None = None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def instructor(user: User, course: Course) -> None:
    profile = Instructor.objects.create(slug=f"u{user.pk}", full_name=user.first_name, user=user)
    course.instructors.add(profile)


def ids(items: list[dict[str, Any]], *texts: str) -> list[int]:
    by_text = {item["text"]: item["id"] for item in items}
    return [by_text[text] for text in texts]


def right_answer(question: dict[str, Any]) -> dict[str, Any]:
    """Savolga to'g'ri javob — brauzer ko'rgan ma'lumot (matn va o'rinlar) bo'yicha."""
    kind = question["kind"]
    if kind == "SINGLE":
        return {"choice": ids(question["options"], "HyperText Markup Language")[0]}
    if kind == "MULTIPLE":
        return {"choices": ids(question["options"], "<div>", "<p>")}
    if kind == "TEXT":
        return {"text": "  <H1>. "}
    if kind == "ORDER":
        return {"order": ids(question["items"], *STEPS)}
    left = {item["text"]: item["id"] for item in question["left"]}
    right = {item["text"]: item["id"] for item in question["right"]}
    return {"pairs": {str(left[key]): right[value] for key, value in PAIRS.items()}}


def wrong_answer(question: dict[str, Any]) -> dict[str, Any]:
    kind = question["kind"]
    if kind == "SINGLE":
        return {"choice": ids(question["options"], "High Tech Modern Language")[0]}
    if kind == "MULTIPLE":
        return {"choices": ids(question["options"], "<div>")}
    if kind == "TEXT":
        return {"text": "h2"}
    if kind == "ORDER":
        return {"order": ids(question["items"], *reversed(STEPS))}
    pairs = right_answer(question)["pairs"]
    first, second, *_rest = pairs
    pairs[first], pairs[second] = pairs[second], pairs[first]
    return {"pairs": pairs}


@pytest.fixture
def world(db: Any) -> World:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="frontend", title_uz="Frontend", category=category)
    module = Module.objects.create(course=course, title_uz="HTML")
    lessons = [
        Lesson.objects.create(module=module, title_uz=f"Dars {index}", order=index)
        for index in range(3)
    ]
    quiz = Quiz.objects.create(lesson=lessons[0], title="HTML asoslari", shuffle_questions=False)
    import_questions(quiz, parse(SOURCE))
    student = make_user("+998901000001", Role.STUDENT, name="Aziz")
    teacher = make_user("+998901000002", Role.TEACHER, name="Ustoz")
    # Onlayn guruh: offlayn guruhda vazifalar ustoz "Dars o'tildi" deganda ochiladi (live/gates).
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="FE-1", study_format="ONLINE"
    )
    Enrollment.objects.create(user=student, course=course, group=group)
    return World(course, lessons, quiz, student, teacher, group)
