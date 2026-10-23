"""Dars sahifasida slaydlar: o'quvchi ko'radi, ustozga eslatma — faqat o'qituvchi va xodimga."""

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, LessonSlides, Module
from apps.learning.models import Enrollment, StudyGroup
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db


def person(phone: str, *roles: str) -> User:
    user = User.objects.create_user(phone=phone, password="x")
    set_roles(user, roles)
    return user


@pytest.fixture
def lesson(db: Any) -> Lesson:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(
        slug="python", title_uz="Python", category=category, status=Course.Status.PUBLISHED
    )
    module = Module.objects.create(course=course, title_uz="Asoslar")
    item = Lesson.objects.create(module=module, title_uz="8-mavzu: for", order=1)
    LessonSlides.objects.create(
        lesson=item,
        markdown="# for sikli\n\n---\n\n- bir\n- ikki",
        teacher_notes="10 daqiqa nazariya",
    )
    return item


def get(user: User | None, lesson: Lesson) -> dict[str, Any]:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    response = client.get(f"/api/v1/lessons/{lesson.pk}/")
    assert response.status_code == 200, response.content
    return response.json()


def test_student_sees_slides_without_teacher_notes(lesson: Lesson) -> None:
    student = person("+998901000001", Role.STUDENT)
    Enrollment.objects.create(user=student, course=lesson.module.course)

    slides = get(student, lesson)["slides"]

    assert slides["count"] == 2
    assert slides["slides"][0]["kind"] == "cover"
    assert slides["slides"][0]["title"] == [["t", "for sikli"]]
    assert slides["teacher_notes"] == ""


def test_group_teacher_and_admin_see_notes(lesson: Lesson) -> None:
    teacher = person("+998903000001", Role.TEACHER)
    StudyGroup.objects.create(course=lesson.module.course, teacher=teacher, name="Python")
    admin = person("+998909999999", Role.ADMIN)

    assert get(teacher, lesson)["slides"]["teacher_notes"] == "10 daqiqa nazariya"
    assert get(admin, lesson)["slides"]["teacher_notes"] == "10 daqiqa nazariya"


def test_other_teacher_does_not_see_notes(lesson: Lesson) -> None:
    stranger = person("+998903000002", Role.TEACHER)
    other = Course.objects.create(
        slug="frontend", title_uz="Frontend", category=lesson.module.course.category
    )
    StudyGroup.objects.create(course=other, teacher=stranger, name="Frontend")
    Enrollment.objects.create(user=stranger, course=lesson.module.course)

    assert get(stranger, lesson)["slides"]["teacher_notes"] == ""


def test_lesson_without_slides(lesson: Lesson) -> None:
    lesson.slides.delete()
    student = person("+998901000001", Role.STUDENT)
    Enrollment.objects.create(user=student, course=lesson.module.course)

    assert get(student, lesson)["slides"] is None
