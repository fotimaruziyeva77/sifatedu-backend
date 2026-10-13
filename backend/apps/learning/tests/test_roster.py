"""O'qituvchi o'z guruhini boshqaradi: o'quvchi qo'shish (telefon va ism bilan) va chiqarish,
haftalik dars jadvali — darslar o'zi yaratiladi."""

from datetime import time
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bot.accounts import Outcome, register
from apps.catalog.models import Category, Course
from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import LiveLesson, ScheduleSlot
from apps.notifications.models import Notification
from apps.users.models import User
from apps.users.roles import Role, role_names, set_roles

pytestmark = pytest.mark.django_db

URL = "/api/v1/teacher/groups/"


def user_with(phone: str, *roles: str, name: str = "") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name)
    set_roles(user, roles)
    return user


@pytest.fixture
def group(db: Any) -> StudyGroup:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="python", title_uz="Python", category=category)
    teacher = user_with("+998903000001", Role.TEACHER, name="Ustoz")
    return StudyGroup.objects.create(
        course=course, teacher=teacher, name="Python", status=StudyGroup.Status.ACTIVE
    )


def as_teacher(group: StudyGroup) -> APIClient:
    client = APIClient()
    client.force_authenticate(group.teacher)
    return client


def test_teacher_adds_a_new_student_who_later_joins_the_bot(
    group: StudyGroup, django_capture_on_commit_callbacks: Any
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = as_teacher(group).post(
            f"{URL}{group.pk}/students/",
            {"phone": "90 123 45 67", "first_name": "Jahongir", "last_name": "Karimov"},
            format="json",
        )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert (body["name"], body["created"], body["moved_from"]) == ("Jahongir Karimov", True, "")
    assert [student["name"] for student in body["group"]["students"]] == ["Jahongir Karimov"]
    student = User.objects.get(phone="+998901234567")
    assert not student.has_usable_password() and role_names(student) == {Role.STUDENT}
    enrollment = Enrollment.objects.get(user=student)
    assert (enrollment.status, enrollment.source, enrollment.group, enrollment.study_format) == (
        Enrollment.Status.ACTIVE,
        Enrollment.Source.MANUAL,
        group,
        "OFFLINE",
    )
    assert Notification.objects.filter(user=student, kind=Notification.Kind.COURSE_OPENED).exists()
    # O'quvchi botga shu raqam bilan kirganda — yangi akkaunt emas, o'shanga ulanadi.
    outcome, linked = register("+998901234567", {"id": 777, "first_name": "Jahon"}, "uz")
    assert (outcome, linked) == (Outcome.LINKED, student)


def test_student_from_another_group_is_moved_and_staff_is_refused(group: StudyGroup) -> None:
    other = StudyGroup.objects.create(course=group.course, teacher=group.teacher, name="Python-2")
    student = user_with("+998901112233", Role.STUDENT, name="Aziz")
    Enrollment.objects.create(user=student, course=group.course, group=other)
    user_with("+998901119999", Role.MANAGER, name="Menejer")
    client = as_teacher(group)

    moved = client.post(f"{URL}{group.pk}/students/", {"phone": "+998901112233"}, format="json")
    again = client.post(f"{URL}{group.pk}/students/", {"phone": "+998901112233"}, format="json")
    staff = client.post(f"{URL}{group.pk}/students/", {"phone": "+998901119999"}, format="json")
    nameless = client.post(f"{URL}{group.pk}/students/", {"phone": "+998905550000"}, format="json")
    wrong = client.post(f"{URL}{group.pk}/students/", {"phone": "12345"}, format="json")

    assert moved.status_code == 201 and moved.json()["moved_from"] == "Python-2"
    assert Enrollment.objects.get(user=student).group == group
    assert "allaqachon shu guruhda" in str(again.json())
    assert "xodimga tegishli" in str(staff.json())
    assert "ismini yozing" in str(nameless.json())
    assert "noto'g'ri" in str(wrong.json())


def test_removed_student_leaves_the_group_and_others_cannot_touch_it(group: StudyGroup) -> None:
    student = user_with("+998901112233", Role.STUDENT, name="Aziz")
    Enrollment.objects.create(user=student, course=group.course, group=group)
    stranger = APIClient()
    stranger.force_authenticate(user_with("+998903000009", Role.TEACHER))

    foreign = stranger.delete(f"{URL}{group.pk}/students/{student.pk}/")
    removed = as_teacher(group).delete(f"{URL}{group.pk}/students/{student.pk}/")
    twice = as_teacher(group).delete(f"{URL}{group.pk}/students/{student.pk}/")

    assert foreign.status_code == 404
    assert removed.status_code == 200 and removed.json()["students"] == []
    assert Enrollment.objects.get(user=student).status == Enrollment.Status.CANCELLED
    assert twice.status_code == 400


def test_weekly_schedule_creates_lessons_for_attendance(group: StudyGroup) -> None:
    client = as_teacher(group)

    monday = client.post(
        f"{URL}{group.pk}/slots/", {"weekday": 0, "starts_at": "18:00"}, format="json"
    )
    client.post(f"{URL}{group.pk}/slots/", {"weekday": 2, "starts_at": "18:00"}, format="json")
    duplicate = client.post(
        f"{URL}{group.pk}/slots/", {"weekday": 0, "starts_at": "18:00"}, format="json"
    )

    assert monday.status_code == 201
    assert monday.json()["slots"] == [
        {
            "id": monday.json()["slots"][0]["id"],
            "weekday": 0,
            "starts_at": "18:00",
            "duration_min": 90,
        }
    ]
    group.refresh_from_db()
    assert group.schedule == "Du, Chor — 18:00"
    lessons = LiveLesson.objects.filter(group=group)
    assert {timezone.localtime(lesson.starts_at).weekday() for lesson in lessons} == {0, 2}
    assert all(lesson.kind == LiveLesson.Kind.OFFLINE for lesson in lessons)
    assert "dars bor" in str(duplicate.json())

    slot = ScheduleSlot.objects.get(group=group, weekday=0, starts_at=time(18))
    left = client.delete(f"{URL}{group.pk}/slots/{slot.pk}/")

    assert [item["weekday"] for item in left.json()["slots"]] == [2]
    group.refresh_from_db()
    assert group.schedule == "Chor — 18:00"
    assert {timezone.localtime(lesson.starts_at).weekday() for lesson in lessons.all()} == {2}
