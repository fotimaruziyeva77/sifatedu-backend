"""O'qituvchi: davomat, bekor qilish, yozuv havolasi; kim nima qila oladi."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.live import services
from apps.live.models import Attendance, LiveLesson
from apps.notifications.models import Notification
from apps.users.roles import Role

from .conftest import World, api, live, make_user, soon

pytestmark = pytest.mark.django_db


def url(lesson: LiveLesson, action: str = "") -> str:
    return f"/api/v1/teacher/live/{lesson.pk}/{action + '/' if action else ''}"


def mark(user: Any, lesson: LiveLesson, **statuses: str) -> Any:
    """`statuses` — {"<o'quvchi ID si>": "PRESENT", ...}."""
    return api(user).put(
        url(lesson, "attendance"),
        {"items": [{"student": int(pk), "status": status} for pk, status in statuses.items()]},
        format="json",
    )


def notes(kind: str) -> list[Notification]:
    return list(Notification.objects.filter(kind=kind).order_by("pk"))


def test_teacher_marks_attendance_and_absent_student_is_told_after_class(world: World) -> None:
    lesson = live(world, soon(-5), duration_min=60)

    response = mark(
        world.teacher,
        lesson,
        **{str(world.student.pk): "ABSENT", str(world.classmate.pk): "PRESENT"},
    )

    assert response.status_code == 200, response.json()
    roster = {row["id"]: row["status"] for row in response.json()["students"]}
    assert roster == {world.student.pk: "ABSENT", world.classmate.pk: "PRESENT"}
    record = Attendance.objects.get(live_lesson=lesson, student=world.student)
    assert (record.marked_by, record.status) == (world.teacher, "ABSENT")
    # Dars davomida xabar yo'q: o'qituvchi xatosini tuzatishga ulgursin.
    services.remind(now=lesson.ends_at + timedelta(minutes=5))
    assert notes(Notification.Kind.LIVE_ABSENT) == []
    services.remind(now=lesson.ends_at + timedelta(minutes=16))
    services.remind(now=lesson.ends_at + timedelta(minutes=21))
    [note] = notes(Notification.Kind.LIVE_ABSENT)
    assert (note.user, note.title, note.link) == (
        world.student,
        "Siz darsda bo'lmadingiz",
        "/dashboard/schedule",
    )


def test_joined_student_is_preselected_and_confirmed_by_teacher(world: World) -> None:
    lesson = live(world, soon(3))
    api(world.student).get(f"/api/v1/live/{lesson.pk}/join/")

    before = api(world.teacher).get(url(lesson)).json()
    mark(world.teacher, lesson, **{str(world.student.pk): "PRESENT"})

    statuses = {row["id"]: row["status"] for row in before["students"]}
    assert statuses == {world.student.pk: "PRESENT", world.classmate.pk: ""}
    assert before["can_mark"] is True and before["can_cancel"] is True
    record = Attendance.objects.get(live_lesson=lesson, student=world.student)
    assert record.marked_by == world.teacher


def test_attendance_needs_a_started_lesson_and_known_students(world: World) -> None:
    future = live(world, soon(120))
    canceled = live(world, soon(-5), canceled_at=timezone.now())
    current = live(world, soon(-30))

    too_early = mark(world.teacher, future, **{str(world.student.pk): "PRESENT"})
    on_canceled = mark(world.teacher, canceled, **{str(world.student.pk): "PRESENT"})
    stranger = mark(world.teacher, current, **{str(world.outsider.pk): "PRESENT"})
    wrong = mark(world.teacher, current, **{str(world.student.pk): "MAYBE"})

    for response in (too_early, on_canceled, stranger, wrong):
        assert response.status_code == 400
    assert "15 daqiqa oldin" in str(too_early.json())
    assert not Attendance.objects.exists()


def test_only_group_teacher_manager_and_admin_manage_lessons(world: World) -> None:
    lesson = live(world, soon(-5))
    other_teacher = make_user("+998901000011", Role.TEACHER)
    manager = make_user("+998901000012", Role.MANAGER)
    director = make_user("+998901000013", Role.DIRECTOR)

    codes = [
        api(user).get(url(lesson)).status_code for user in (other_teacher, director, world.student)
    ]
    by_manager = mark(manager, lesson, **{str(world.student.pk): "EXCUSED"})

    assert codes == [404, 404, 404]
    assert by_manager.status_code == 200
    assert api().get(url(lesson)).status_code == 403


def test_teacher_cancels_a_future_lesson_and_students_are_told(world: World) -> None:
    lesson = live(world, soon(180))
    started = live(world, soon(-1))

    response = api(world.teacher).post(url(lesson, "cancel"), {"reason": "Bayram"}, format="json")
    again = api(world.teacher).post(url(lesson, "cancel"), {}, format="json")
    late = api(world.teacher).post(url(started, "cancel"), {}, format="json")

    assert response.status_code == 200
    assert (response.json()["canceled"], response.json()["cancel_reason"]) == (True, "Bayram")
    assert again.status_code == 400 and late.status_code == 400
    received = {note.user for note in notes(Notification.Kind.LIVE_CANCELED)}
    # O'qituvchi o'zi bekor qildi — unga xabar kerak emas.
    assert received == {world.student, world.classmate}
    assert "Sabab: Bayram" in notes(Notification.Kind.LIVE_CANCELED)[0].body


def test_manager_cancel_also_tells_the_teacher(world: World) -> None:
    lesson = live(world, soon(180))
    manager = make_user("+998901000012", Role.MANAGER)

    api(manager).post(url(lesson, "cancel"), {}, format="json")

    received = {note.user for note in notes(Notification.Kind.LIVE_CANCELED)}
    assert received == {world.student, world.classmate, world.teacher}
    assert "Sabab: ko'rsatilmagan" in notes(Notification.Kind.LIVE_CANCELED)[0].body


def test_recording_link_is_shared_once(world: World) -> None:
    lesson = live(world, soon(-200))

    first = api(world.teacher).patch(
        url(lesson), {"recording_url": "https://youtu.be/abc", "notes": "Flexbox"}, format="json"
    )
    api(world.teacher).patch(url(lesson), {"recording_url": "https://youtu.be/abc"}, format="json")
    bad = api(world.teacher).patch(url(lesson), {"recording_url": "yozuv"}, format="json")

    assert first.status_code == 200
    assert (first.json()["recording_url"], first.json()["notes"]) == (
        "https://youtu.be/abc",
        "Flexbox",
    )
    assert bad.status_code == 400
    assert {note.user for note in notes(Notification.Kind.LIVE_RECORDING)} == {
        world.student,
        world.classmate,
    }
    past = api(world.student).get("/api/v1/live/", {"when": "past"}).json()
    assert (past[0]["recording_url"], past[0]["notes"]) == ("https://youtu.be/abc", "Flexbox")
