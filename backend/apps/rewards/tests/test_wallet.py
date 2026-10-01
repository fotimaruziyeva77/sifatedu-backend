"""Hamyon va hodisalar: bir harakat — bir mukofot, shtraf 0 dan pastga tushmaydi, bekor qilish."""

from typing import Any
from unittest import mock

import pytest

from apps.core import events
from apps.live.models import LiveLesson
from apps.rewards import services
from apps.rewards.models import Entry, GameSettings, Wallet

from .conftest import World

pytestmark = pytest.mark.django_db
Reason = Entry.Reason


def wallet(world: World) -> Wallet:
    return Wallet.objects.get(user=world.student)


def test_reward_is_given_once_per_key(world: World) -> None:
    first = services.reward(world.student.pk, Reason.LESSON, 10, key="lesson:1:1")
    again = services.reward(world.student.pk, Reason.LESSON, 10, key="lesson:1:1")

    assert first is not None and again is None
    assert (wallet(world).xp, wallet(world).coins) == (10, 10)


def test_penalty_never_goes_below_zero_and_cancel_returns_it(world: World) -> None:
    services.reward(world.student.pk, Reason.LESSON, 10, key="lesson:a")
    penalty = services.penalize(world.student.pk, Reason.ABSENT, 15, key="live:a")

    assert penalty is not None and penalty.applied_xp == -10
    assert (wallet(world).xp, wallet(world).coins) == (0, 10)

    services.cancel(penalty, by=world.teacher, reason="Kasal edi")
    assert wallet(world).xp == 10
    with pytest.raises(services.RewardError, match="allaqachon"):
        services.cancel(penalty)
    # Bekor qilingan kalit bilan yangi yozuv mumkin (masalan, davomat qayta o'zgarsa).
    assert services.penalize(world.student.pk, Reason.ABSENT, 15, key="live:a") is not None


def test_coins_cannot_go_negative(world: World) -> None:
    with pytest.raises(services.RewardError, match="Coin yetarli emas"):
        services.credit(world.student.pk, Reason.PURCHASE, key="shop:1", coins=-5)


def test_learning_events_give_xp_and_coins(world: World) -> None:
    user, course = world.student.pk, world.course.pk
    events.lesson_completed.send(None, user_id=user, course_id=course, lesson_id=1)
    events.lesson_completed.send(None, user_id=user, course_id=course, lesson_id=1)
    events.quiz_passed.send(None, user_id=user, course_id=course, quiz_id=5, first=True)
    events.quiz_passed.send(None, user_id=user, course_id=course, quiz_id=6, first=False)
    events.homework_submitted.send(
        None, user_id=user, course_id=course, assignment_id=7, lesson_id=1, late=True
    )
    events.exam_finalized.send(None, user_id=user, course_id=course, exam_id=3, passed=True)

    reasons = sorted(Entry.objects.filter(user=world.student).values_list("reason", "applied_xp"))
    assert reasons == [
        ("EXAM", 50),
        ("HOMEWORK", 20),
        ("HOMEWORK_LATE", -10),
        ("LESSON", 10),
        ("QUIZ", 15),
    ]
    assert (wallet(world).xp, wallet(world).coins) == (85, 95)


def test_attendance_change_replaces_the_previous_entry(world: World) -> None:
    services.reward(world.student.pk, Reason.LESSON, 30, key="seed")
    args = {"user_id": world.student.pk, "course_id": world.course.pk, "live_lesson_id": 9}

    events.attendance_marked.send(LiveLesson, status="ABSENT", **args)
    assert wallet(world).xp == 15
    events.attendance_marked.send(LiveLesson, status="PRESENT", **args)
    assert wallet(world).xp == 40
    events.attendance_marked.send(LiveLesson, status="PRESENT", **args)
    events.attendance_marked.send(LiveLesson, status="EXCUSED", **args)

    assert wallet(world).xp == 30
    active = Entry.objects.filter(user=world.student, canceled_at__isnull=True)
    assert list(active.values_list("reason", flat=True)) == ["LESSON"]


def test_settings_change_the_points(world: World) -> None:
    config = GameSettings.load()
    config.lesson_xp = 25
    config.save()

    events.lesson_completed.send(
        None, user_id=world.student.pk, course_id=world.course.pk, lesson_id=2
    )

    assert wallet(world).xp == 25


def test_reward_errors_do_not_break_learning(world: World, caplog: Any) -> None:
    with mock.patch.object(services, "reward", side_effect=RuntimeError("buzildi")):
        events.lesson_completed.send(
            None, user_id=world.student.pk, course_id=world.course.pk, lesson_id=2
        )

    assert "Mukofot hisoblanmadi" in caplog.text
