"""Yutuqlar API va o'qituvchining shtrafni bekor qilishi."""

import pytest
from django.utils import timezone

from apps.rewards import services
from apps.rewards.models import DailyTask, Entry, Wallet

from .conftest import World, api, make_user

pytestmark = pytest.mark.django_db
Reason = Entry.Reason


def test_rewards_page_data(world: World) -> None:
    services.reward(world.student.pk, Reason.LESSON, 10, key="a", course_id=world.course.pk)
    services.penalize(world.student.pk, Reason.LATE, 5, key="b")
    DailyTask.objects.create(
        user=world.student,
        day=timezone.localdate(),
        kind=DailyTask.Kind.LESSON,
        course=world.course,
        lesson=world.lessons[1],
        title="Dars 2",
    )

    data = api(world.student).get("/api/v1/rewards/").json()

    assert (data["xp"], data["coins"], data["streak"]) == (5, 10, 0)
    [task] = data["tasks"]
    assert task["url"] == f"/dashboard/courses/frontend/lessons/{world.lessons[1].pk}"
    assert task["done"] is False
    assert [(row["reason"], row["xp"], row["penalty"]) for row in data["history"]] == [
        ("LATE", -5, True),
        ("LESSON", 10, False),
    ]
    assert data["history"][1]["course_title"] == "Frontend"
    assert data["invite_url"].endswith(f"?ref={world.student.referral_code}")


def test_history_pages(world: World) -> None:
    for index in range(35):
        services.reward(world.student.pk, Reason.MANUAL, 1, key=f"m{index}")
    client = api(world.student)

    first = client.get("/api/v1/rewards/history/").json()
    second = client.get("/api/v1/rewards/history/?page=2").json()

    assert (len(first["results"]), first["next_page"]) == (30, 2)
    assert (len(second["results"]), second["next_page"]) == (5, None)


def test_hide_from_rating(world: World) -> None:
    response = api(world.student).patch(
        "/api/v1/rewards/settings/", {"hidden": True}, format="json"
    )

    assert response.json() == {"hidden": True}
    assert Wallet.objects.get(user=world.student).hidden is True


def test_teacher_cancels_a_penalty_of_own_student(world: World) -> None:
    services.reward(world.student.pk, Reason.LESSON, 20, key="a")
    penalty = services.penalize(world.student.pk, Reason.ABSENT, 15, key="live:1")
    assert penalty is not None
    client = api(world.teacher)

    [row] = client.get(f"/api/v1/teacher/penalties/?group={world.group.pk}").json()
    assert (row["student_name"], row["xp"], row["can_cancel"]) == ("Aziz Valiyev", -15, True)
    canceled = client.post(
        f"/api/v1/teacher/penalties/{penalty.pk}/cancel/", {"reason": "Kasal edi"}, format="json"
    )

    assert canceled.status_code == 200 and canceled.json()["canceled"] is True
    assert Wallet.objects.get(user=world.student).xp == 20

    other = make_user("+998901000003", "TEACHER", name="Boshqa")
    again = services.penalize(world.student.pk, Reason.LATE, 5, key="live:2")
    assert again is not None
    assert api(other).get("/api/v1/teacher/penalties/").json() == []
    assert (
        api(other)
        .post(f"/api/v1/teacher/penalties/{again.pk}/cancel/", {"reason": "x"}, format="json")
        .status_code
        == 404
    )
    assert api(world.student).get("/api/v1/teacher/penalties/").status_code == 403


def test_rewards_are_not_cancelable_by_teachers(world: World) -> None:
    entry = services.reward(world.student.pk, Reason.LESSON, 20, key="a")
    assert entry is not None

    response = api(world.teacher).post(
        f"/api/v1/teacher/penalties/{entry.pk}/cancel/", {"reason": "x"}, format="json"
    )

    assert response.status_code == 404
