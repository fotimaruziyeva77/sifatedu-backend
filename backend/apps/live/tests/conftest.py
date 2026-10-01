from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import LiveLesson, ScheduleSlot
from apps.users.models import User
from apps.users.roles import Role, set_roles

MEET = "https://meet.google.com/abc-defg-hij"
# 2026-yil 5-oktabr — dushanba.
MONDAY = datetime(2026, 10, 5)


@dataclass
class World:
    course: Course
    lessons: list[Lesson]
    group: StudyGroup
    teacher: User
    student: User
    classmate: User
    outsider: User


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


def local(day: datetime, at: str) -> datetime:
    """Toshkent vaqti: `local(MONDAY, "18:00")`."""
    hours, minutes = (int(part) for part in at.split(":"))
    moment = datetime.combine(day.date(), time(hours, minutes))
    return timezone.make_aware(moment, timezone.get_default_timezone())


def live(world: World, starts_at: datetime, **extra: Any) -> LiveLesson:
    return LiveLesson.objects.create(
        group=world.group,
        starts_at=starts_at,
        meet_url=extra.pop("meet_url", MEET),
        **extra,
    )


def soon(minutes: int) -> datetime:
    return timezone.now() + timedelta(minutes=minutes)


@pytest.fixture
def world(db: Any) -> World:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="frontend", title_uz="Frontend", category=category)
    module = Module.objects.create(course=course, title_uz="HTML")
    lessons = [
        Lesson.objects.create(module=module, title_uz=f"Dars {index}", order=index)
        for index in range(1, 3)
    ]
    teacher = make_user("+998901000002", Role.TEACHER, name="Ustoz")
    group = StudyGroup.objects.create(
        course=course,
        teacher=teacher,
        name="FE-1",
        study_format="ONLINE",
        status=StudyGroup.Status.ACTIVE,
        meet_url=MEET,
    )
    ScheduleSlot.objects.create(group=group, weekday=0, starts_at=time(18, 0))
    ScheduleSlot.objects.create(group=group, weekday=2, starts_at=time(18, 0), duration_min=120)
    student = make_user("+998901000001", Role.STUDENT, name="Aziz")
    classmate = make_user("+998901000003", Role.STUDENT, name="Bekzod")
    outsider = make_user("+998901000004", Role.STUDENT, name="Chori")
    for user in (student, classmate):
        Enrollment.objects.create(user=user, course=course, group=group)
    Enrollment.objects.create(user=outsider, course=course)
    return World(course, lessons, group, teacher, student, classmate, outsider)
