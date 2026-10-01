import io
from dataclasses import dataclass
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Instructor, Lesson, Module
from apps.homework.models import Assignment
from apps.learning.models import Enrollment, StudyGroup
from apps.users.models import User
from apps.users.roles import Role, set_roles


@dataclass
class World:
    course: Course
    lessons: list[Lesson]
    assignment: Assignment
    student: User
    teacher: User
    group: StudyGroup


def make_user(phone: str, *roles: str, name: str = "") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name or phone[-4:])
    if roles:
        set_roles(user, roles)
    return user


def api(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def png(name: str = "rasm.png") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def world(db: Any) -> World:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="frontend", title_uz="Frontend", category=category)
    module = Module.objects.create(course=course, title_uz="HTML")
    lessons = [
        Lesson.objects.create(module=module, title_uz=f"Dars {index}", order=index)
        for index in range(3)
    ]
    assignment = Assignment.objects.create(
        lesson=lessons[0], title="Sahifa", instructions="Kichik sahifa yasang."
    )
    student = make_user("+998901000001", Role.STUDENT, name="Aziz")
    teacher = make_user("+998901000002", Role.TEACHER, name="Ustoz")
    # Onlayn guruh: offlayn guruhda vazifalar ustoz "Dars o'tildi" deganda ochiladi (live/gates).
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="FE-1", study_format="ONLINE"
    )
    Enrollment.objects.create(user=student, course=course, group=group)
    return World(course, lessons, assignment, student, teacher, group)


def instructor(user: User, course: Course) -> None:
    profile = Instructor.objects.create(slug=f"u{user.pk}", full_name=user.first_name, user=user)
    course.instructors.add(profile)
