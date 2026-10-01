"""Reyting: davr, doira, yashirinlar, bosh harf va o'z o'rni."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.learning.models import Enrollment
from apps.rewards import rating, services
from apps.rewards.models import Entry, Wallet

from .conftest import World, api, make_user

pytestmark = pytest.mark.django_db
Reason = Entry.Reason


def test_weekly_board_counts_this_weeks_xp(world: World) -> None:
    services.reward(world.student.pk, Reason.LESSON, 30, key="a")
    services.reward(world.friend.pk, Reason.LESSON, 50, key="b")
    old = services.reward(world.friend.pk, Reason.LESSON, 100, key="c")
    assert old is not None
    Entry.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=40))

    week = rating.board(world.student, "course", world.course.pk, "week")
    total = rating.board(world.student, "course", world.course.pk, "all")

    assert [(row["name"], row["xp"]) for row in week["top"]] == [
        ("Bekzod K.", 50),
        ("Aziz V.", 30),
    ]
    assert week["me"] == {"place": 2, "xp": 30, "hidden": False}
    assert [row["xp"] for row in total["top"]] == [150, 30]


def test_hidden_students_are_not_listed(world: World) -> None:
    services.reward(world.student.pk, Reason.LESSON, 30, key="a")
    services.reward(world.friend.pk, Reason.LESSON, 50, key="b")
    Wallet.objects.filter(user=world.friend).update(hidden=True)

    board = rating.board(world.student, "group", world.group.pk, "month")
    mine = rating.board(world.friend, "group", world.group.pk, "month")

    assert [row["name"] for row in board["top"]] == ["Aziz V."]
    assert mine["me"] == {"place": None, "xp": 50, "hidden": True}


def test_rating_api_scopes_and_permissions(world: World) -> None:
    services.reward(world.student.pk, Reason.LESSON, 30, key="a")
    client = api(world.student)

    data = client.get("/api/v1/rewards/rating/").json()
    assert data["scope"] == "course" and data["period"] == "week"
    assert {(scope["kind"], scope["title"]) for scope in data["scopes"]} == {
        ("course", "Frontend"),
        ("group", "FE-1"),
    }
    group = client.get(f"/api/v1/rewards/rating/?scope=group&id={world.group.pk}&period=all")
    assert group.json()["top"][0]["me"] is True

    stranger = make_user("+998901000009")
    assert (
        api(stranger).get(f"/api/v1/rewards/rating/?scope=course&id={world.course.pk}").status_code
        == 404
    )
    assert client.get("/api/v1/rewards/rating/?period=year").status_code == 400


def test_weekly_winners_skip_staff_and_hidden(world: World) -> None:
    services.reward(world.student.pk, Reason.LESSON, 30, key="a")
    services.reward(world.friend.pk, Reason.LESSON, 50, key="b")
    Enrollment.objects.filter(user=world.friend).update(status=Enrollment.Status.ACTIVE)
    Entry.objects.update(created_at=timezone.now() - timedelta(days=7))
    Wallet.objects.filter(user=world.student).update(hidden=True)

    winners = rating.weekly_winners()

    assert [(person.pk, points) for person, points in winners] == [(world.friend.pk, 50)]
