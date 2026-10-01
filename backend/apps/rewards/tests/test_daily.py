"""Kunlik topshiriqlar: tanlash, bajarilishi, bonus va seriya, kun oxiridagi shtraf."""

from datetime import datetime, timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.core import events
from apps.live.models import LiveLesson
from apps.quizzes.models import Attempt
from apps.rewards import daily
from apps.rewards.models import DailyTask, Entry, GameSettings, Wallet

from .conftest import World

pytestmark = pytest.mark.django_db
Kind = DailyTask.Kind


def at(hour: int, *, days: int = 0) -> datetime:
    local = timezone.localtime().replace(hour=hour, minute=0, second=0, microsecond=0)
    return local + timedelta(days=days)


def kinds(user: Any, day: Any) -> set[str]:
    return set(DailyTask.objects.filter(user=user, day=day).values_list("kind", flat=True))


def test_three_tasks_by_progress_and_todays_class_first(world: World) -> None:
    morning = at(9)
    LiveLesson.objects.create(
        group=world.group, starts_at=morning + timedelta(hours=9), kind=LiveLesson.Kind.OFFLINE
    )

    assert daily.generate(now=morning) == 2  # o'quvchi va do'st
    tasks = DailyTask.objects.filter(user=world.student, day=morning.date())
    assert tasks.count() == 3
    assert Kind.LIVE in kinds(world.student, morning.date())
    lesson_task = tasks.filter(kind=Kind.LESSON).first()
    assert lesson_task is None or lesson_task.lesson_id == world.lessons[0].pk
    # Qayta ishga tushsa — yangi topshiriq yo'q.
    assert daily.generate(now=morning) == 0


def test_tasks_can_be_switched_off(world: World) -> None:
    config = GameSettings.load()
    config.daily_tasks = False
    config.save()

    assert daily.generate(now=at(9)) == 0


def test_completing_all_tasks_gives_bonus_and_streak(world: World) -> None:
    day = at(9)
    for kind in (Kind.LESSON, Kind.QUIZ):
        DailyTask.objects.create(user=world.student, day=day.date(), kind=kind)
    Wallet.objects.create(user=world.student, streak=4, streak_day=day.date() - timedelta(days=1))

    events.lesson_completed.send(
        None,
        user_id=world.student.pk,
        course_id=world.course.pk,
        lesson_id=world.lessons[0].pk,
    )
    assert not Entry.objects.filter(reason=Entry.Reason.DAILY).exists()
    events.quiz_passed.send(
        None, user_id=world.student.pk, course_id=world.course.pk, quiz_id=1, first=False
    )

    bonus = Entry.objects.get(reason=Entry.Reason.DAILY)
    assert bonus.applied_xp == 10
    wallet = Wallet.objects.get(user=world.student)
    assert (wallet.streak, wallet.best_streak, wallet.streak_day) == (5, 5, day.date())


def test_a_day_without_tasks_keeps_the_streak_but_a_missed_day_breaks_it(world: World) -> None:
    today = timezone.localdate()
    Wallet.objects.create(user=world.student, streak=3, streak_day=today - timedelta(days=3))
    DailyTask.objects.create(user=world.student, day=today, kind=Kind.LESSON)

    daily.progress(world.student.pk, Kind.LESSON, course_id=world.course.pk)
    assert Wallet.objects.get(user=world.student).streak == 4

    DailyTask.objects.create(user=world.friend, day=today - timedelta(days=1), kind=Kind.QUIZ)
    DailyTask.objects.create(user=world.friend, day=today, kind=Kind.QUIZ)
    Wallet.objects.create(user=world.friend, streak=7, streak_day=today - timedelta(days=2))
    daily.progress(world.friend.pk, Kind.QUIZ, course_id=world.course.pk)
    assert Wallet.objects.get(user=world.friend).streak == 1


def test_missed_tasks_are_fined_at_night(world: World) -> None:
    yesterday = timezone.localdate() - timedelta(days=1)
    DailyTask.objects.create(user=world.student, day=yesterday, kind=Kind.LESSON)
    DailyTask.objects.create(
        user=world.friend, day=yesterday, kind=Kind.LESSON, done_at=timezone.now()
    )
    Wallet.objects.create(user=world.student, xp=20, streak=2)

    assert daily.close() == 1
    assert daily.close() == 0  # bir marta

    wallet = Wallet.objects.get(user=world.student)
    assert (wallet.xp, wallet.streak) == (15, 0)
    assert not Entry.objects.filter(user=world.friend).exists()


def test_quiz_task_is_the_first_open_quiz(world: World) -> None:
    task = daily.open_quiz(world.student)
    assert task is not None and task.quiz_id == world.quiz.pk

    Attempt.objects.create(quiz=world.quiz, student=world.student, passed=True, score=100)
    assert daily.open_quiz(world.student) is None
