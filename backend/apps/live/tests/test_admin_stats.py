"""Admin (jadval, darslar, davomat), guruh sahifasi va "muammolar"."""

from datetime import time, timedelta
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.live import services
from apps.live.models import Attendance, ScheduleSlot
from apps.notifications.models import Notification
from apps.stats import metrics
from apps.users.models import User
from apps.users.roles import Role

from .conftest import World, api, live, make_user, soon

pytestmark = pytest.mark.django_db


def login(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def absent(world: World, *starts: Any, student: User | None = None) -> None:
    for moment in starts:
        lesson = live(world, moment)
        Attendance.objects.create(
            live_lesson=lesson, student=student or world.student, status="ABSENT"
        )


def test_group_page_shows_attendance_rate_and_lessons(world: World) -> None:
    for offset, status in ((-4, "PRESENT"), (-3, "LATE"), (-2, "ABSENT"), (-1, "EXCUSED")):
        lesson = live(world, soon(offset * 24 * 60))
        Attendance.objects.create(live_lesson=lesson, student=world.student, status=status)
    upcoming = live(world, soon(60))

    body = api(world.teacher).get(f"/api/v1/teacher/groups/{world.group.pk}/").json()

    rates = {student["id"]: student["attendance_rate"] for student in body["students"]}
    assert rates == {world.student.pk: 67, world.classmate.pk: None}
    assert [lesson["id"] for lesson in body["lessons"]][-1] == upcoming.pk
    assert [(lesson["marked"], lesson["came"]) for lesson in body["lessons"][:4]] == [
        (1, 1),
        (1, 1),
        (1, 0),
        (1, 0),
    ]


def test_two_absences_in_a_row_are_a_problem(world: World) -> None:
    absent(world, soon(-3 * 24 * 60), soon(-24 * 60))

    found = {item.title: item for item in metrics.problems(metrics.period("today"))}

    assert found["Ketma-ket 2 marta darsga kelmagan o'quvchilar"].count == 1
    # Oxirgi darsga kelsa — muammo yo'qoladi.
    lesson = live(world, soon(-60))
    Attendance.objects.create(live_lesson=lesson, student=world.student, status="PRESENT")
    assert services.repeated_absences() == []


def test_schedule_slots_in_group_admin_create_lessons(world: World) -> None:
    admin = User.objects.create_superuser(phone="+998900000009", password="x")
    world.group.slots.all().delete()
    url = reverse("admin:learning_studygroup_change", args=[world.group.pk])
    page = login(admin).get(url)
    form: dict[str, Any] = {
        "name": world.group.name,
        "course": world.course.pk,
        "teacher": world.teacher.pk,
        "study_format": "ONLINE",
        "schedule": "Seshanba 17:00",
        "starts_on": "",
        "meet_url": "https://meet.google.com/abc-defg-hij",
        "room": "",
        "capacity": "",
        "status": "ACTIVE",
        "students": list(world.group.enrollments.values_list("pk", flat=True)),
        "slots-TOTAL_FORMS": "1",
        "slots-INITIAL_FORMS": "0",
        "slots-MIN_NUM_FORMS": "0",
        "slots-MAX_NUM_FORMS": "1000",
        "slots-0-weekday": "1",
        "slots-0-starts_at": "17:00",
        "slots-0-duration_min": "90",
        "covered_lessons-TOTAL_FORMS": "0",
        "covered_lessons-INITIAL_FORMS": "0",
        "covered_lessons-MIN_NUM_FORMS": "0",
        "covered_lessons-MAX_NUM_FORMS": "1000",
    }

    response = login(admin).post(url, form, follow=True)

    assert page.status_code == 200
    assert response.status_code == 200
    assert ScheduleSlot.objects.get(group=world.group).starts_at == time(17, 0)
    lessons = world.group.live_lessons.all()
    # Nechta seshanba chiqishi bugungi kun va soatga bog'liq (14 kun ichida 1–2 ta).
    assert lessons.count() == len(services.planned_times(world.group)) > 0
    assert all(timezone.localtime(lesson.starts_at).weekday() == 1 for lesson in lessons)
    assert world.group.enrollments.count() == 2
    assert "Jonli darslar yangilandi" in response.content.decode()


def test_teacher_sees_only_own_group_lessons_in_admin(world: World) -> None:
    live(world, soon(60))
    other = make_user("+998901000011", Role.TEACHER)

    for user, expected in ((world.teacher, 1), (other, 0)):
        page = login(user).get(reverse("admin:live_livelesson_changelist"))
        assert page.status_code == 200
        assert len(page.context["cl"].result_list) == expected


def test_admin_edit_keeps_lesson_and_shares_recording(world: World) -> None:
    lesson = live(world, soon(-200), generated=True)
    admin = User.objects.create_superuser(phone="+998900000009", password="x")
    local = timezone.localtime(lesson.starts_at)
    form = {
        "group": world.group.pk,
        "starts_at_0": f"{local:%Y-%m-%d}",
        "starts_at_1": f"{local:%H:%M:%S}",
        "duration_min": "90",
        "kind": "ONLINE",
        "meet_url": lesson.meet_url,
        "room": "",
        "topic": "",
        "title": "Flexbox",
        "notes": "",
        "recording_url": "https://youtu.be/abc",
        "cancel_reason": "",
        "attendance-TOTAL_FORMS": "0",
        "attendance-INITIAL_FORMS": "0",
        "attendance-MIN_NUM_FORMS": "0",
        "attendance-MAX_NUM_FORMS": "1000",
    }

    response = login(admin).post(reverse("admin:live_livelesson_change", args=[lesson.pk]), form)

    assert response.status_code == 302, response.content.decode()[:2000]
    lesson.refresh_from_db()
    assert (lesson.title, lesson.generated) == ("Flexbox", False)
    assert Notification.objects.filter(kind=Notification.Kind.LIVE_RECORDING).count() == 2


def test_cancel_action_notifies_group(world: World) -> None:
    lesson = live(world, soon(300))
    admin = User.objects.create_superuser(phone="+998900000009", password="x")

    login(admin).post(
        reverse("admin:live_livelesson_changelist"),
        {"action": "cancel_selected", "_selected_action": [lesson.pk]},
    )

    lesson.refresh_from_db()
    assert lesson.is_canceled
    assert Notification.objects.filter(kind=Notification.Kind.LIVE_CANCELED).count() == 3
    assert timezone.now() - lesson.canceled_at < timedelta(minutes=1)  # type: ignore[operator]
