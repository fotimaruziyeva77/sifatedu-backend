"""Jadval sahifasi, "Qo'shilish" va kabinet menyusi."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import Attendance, LiveLesson

from .conftest import MEET, World, api, live, make_user, soon

pytestmark = pytest.mark.django_db


def schedule(user: Any, when: str = "upcoming") -> list[dict[str, Any]]:
    response = api(user).get("/api/v1/live/", {"when": when})
    assert response.status_code == 200
    body: list[dict[str, Any]] = response.json()
    return body


def test_student_sees_own_group_lessons(world: World) -> None:
    starting = live(world, soon(10), title="Flexbox")
    later = live(world, soon(60 * 26), kind="OFFLINE", meet_url="", room="3-xona")
    canceled = live(world, soon(60 * 50), canceled_at=timezone.now(), cancel_reason="Bayram")
    past = live(world, soon(-60 * 24), recording_url="https://youtu.be/abc")
    Attendance.objects.create(live_lesson=past, student=world.student, status="LATE")
    # Boshqa guruh (o'quvchi unda emas) darsi ko'rinmaydi.
    other = StudyGroup.objects.create(course=world.course, teacher=world.teacher, name="FE-2")
    LiveLesson.objects.create(group=other, starts_at=soon(20), meet_url=MEET)

    upcoming = schedule(world.student)
    before = schedule(world.student, "past")

    assert [item["id"] for item in upcoming] == [starting.pk, later.pk, canceled.pk]
    first = upcoming[0]
    assert (first["title"], first["group"], first["course_title"]) == (
        "Flexbox",
        "FE-1",
        "Frontend",
    )
    assert first["can_join"] is True and first["join_url"] == f"/api/v1/live/{starting.pk}/join/"
    assert first["is_teacher"] is False and first["recording_url"] == ""
    assert (upcoming[1]["join_url"], upcoming[1]["room"], upcoming[1]["can_join"]) == (
        "",
        "3-xona",
        False,
    )
    assert (upcoming[2]["canceled"], upcoming[2]["cancel_reason"], upcoming[2]["join_url"]) == (
        True,
        "Bayram",
        "",
    )
    [done] = before
    assert (done["id"], done["attendance"], done["recording_url"]) == (
        past.pk,
        "LATE",
        "https://youtu.be/abc",
    )
    assert schedule(world.outsider) == []


def test_teacher_sees_own_groups_only(world: World) -> None:
    lesson = live(world, soon(90))
    stranger = make_user("+998901000009", "TEACHER")

    [item] = schedule(world.teacher)

    assert (item["id"], item["is_teacher"], item["attendance"]) == (lesson.pk, True, None)
    assert schedule(stranger) == []


def test_join_redirects_and_marks_presence(world: World) -> None:
    lesson = live(world, soon(10))

    response = api(world.student).get(f"/api/v1/live/{lesson.pk}/join/")
    again = api(world.student).get(f"/api/v1/live/{lesson.pk}/join/")

    assert (response.status_code, response["Location"]) == (302, MEET)
    assert again.status_code == 302
    record = Attendance.objects.get(live_lesson=lesson, student=world.student)
    assert (record.status, record.marked_by) == ("PRESENT", None)
    assert record.joined_at is not None


def test_late_join_is_marked_late(world: World) -> None:
    lesson = live(world, soon(-20))

    api(world.classmate).get(f"/api/v1/live/{lesson.pk}/join/")

    assert Attendance.objects.get(live_lesson=lesson, student=world.classmate).status == "LATE"


def test_join_outside_the_window_goes_back_to_schedule(world: World) -> None:
    early = live(world, soon(60))
    canceled = live(world, soon(5), canceled_at=timezone.now())
    finished = live(world, soon(-200))

    for lesson in (early, canceled, finished):
        response = api(world.student).get(f"/api/v1/live/{lesson.pk}/join/")
        assert response.status_code == 302
        assert response["Location"] == f"/uz/dashboard/schedule?closed={lesson.pk}"
    assert not Attendance.objects.exists()


def test_join_is_for_group_members_and_teacher(world: World) -> None:
    lesson = live(world, soon(5))
    expired = world.classmate.enrollments.get()
    Enrollment.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(days=1))

    outsider = api(world.outsider).get(f"/api/v1/live/{lesson.pk}/join/")
    teacher = api(world.teacher).get(f"/api/v1/live/{lesson.pk}/join/")
    anonymous = api().get(f"/api/v1/live/{lesson.pk}/join/")
    unpaid = api(world.classmate).get(f"/api/v1/live/{lesson.pk}/join/")

    assert outsider.status_code == 404
    assert (teacher.status_code, teacher["Location"]) == (302, MEET)
    assert anonymous.status_code == 403
    # To'lov muddati o'tgan o'quvchi guruh a'zosi hisoblanmaydi.
    assert unpaid.status_code == 404
    assert not Attendance.objects.exists()


def test_menu_knows_who_has_a_schedule(world: World) -> None:
    def me(user: Any) -> bool:
        flag: bool = api(user).get("/api/v1/me/").json()["has_schedule"]
        return flag

    assert (me(world.student), me(world.teacher), me(world.outsider)) == (True, True, False)
