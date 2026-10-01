"""Botda "✅ Bugungi topshiriqlar", takrorlash (5 savol) va ertalabki xabar."""

from typing import Any

import pytest
from django.utils import timezone

from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.quizzes.models import Attempt, Question
from apps.quizzes.services import Layout
from apps.rewards import announce
from apps.rewards.models import DailyTask, ReviewAttempt

from .conftest import TG_ID, FakeTelegram, World, buttons, connect, message, press

pytestmark = pytest.mark.django_db
Kind = DailyTask.Kind
STEPS = ["HTML o'qiladi", "CSS qo'llanadi", "JavaScript ishga tushadi"]
PAIRS = {"HTML": "tuzilma", "CSS": "ko'rinish", "JavaScript": "harakat"}


def tasks(world: World) -> None:
    day = timezone.localdate()
    DailyTask.objects.create(
        user=world.student,
        day=day,
        kind=Kind.LESSON,
        course=world.course,
        lesson=world.lessons[1],
        title="Dars 2",
    )
    DailyTask.objects.create(
        user=world.student, day=day, kind=Kind.QUIZ, quiz=world.quiz, title="Dars 1"
    )
    DailyTask.objects.create(user=world.student, day=day, kind=Kind.REVIEW)


def state() -> dict[str, Any]:
    return dict(BotChat.objects.get(chat_id=TG_ID).state.get("quiz") or {})


def spot(layout: Layout, text: str, *, match: bool = False) -> int:
    values = [item.match if match else item.text for item in layout.shown]
    return values.index(text) + 1


def answer_right() -> None:
    now = state()
    attempt = ReviewAttempt.objects.get(pk=now["a"])
    question = Question.objects.get(pk=now["q"])
    layout = Layout.build(question, attempt.seed)
    ref = f"{attempt.pk}:{question.pk}"
    if question.kind == Question.Kind.SINGLE:
        handle_update(press(f"qa:{ref}:{spot(layout, 'HyperText Markup Language')}"))
    elif question.kind == Question.Kind.MULTIPLE:
        for text in ["<div>", "<p>"]:
            handle_update(press(f"qt:{ref}:{spot(layout, text)}"))
        handle_update(press(f"qd:{ref}"))
    elif question.kind == Question.Kind.TEXT:
        handle_update(message("h1"))
    elif question.kind == Question.Kind.ORDER:
        for text in STEPS:
            handle_update(press(f"qo:{ref}:{spot(layout, text)}"))
    else:
        for item in layout.choices:
            handle_update(press(f"qm:{ref}:{spot(layout, PAIRS[item.text], match=True)}"))


def test_todays_tasks_in_bot(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    tasks(world)

    handle_update(message("✅ Bugungi topshiriqlar"))

    text = tg.last["text"]
    assert "Bugungi topshiriqlar" in text and "⬜ 1." in text and "Dars 2" in text
    lesson, quiz, review = buttons(tg.last)
    assert "/api/v1/bot/login/" in lesson["url"]
    assert quiz["callback_data"] == f"qs:{world.quiz.pk}"
    assert review["callback_data"] == "rv"


def test_review_in_bot_completes_the_daily_task(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    tasks(world)
    Attempt.objects.create(quiz=world.quiz, student=world.student, passed=True, score=100)

    handle_update(press("rv"))
    for _index in range(5):
        answer_right()

    attempt = ReviewAttempt.objects.get()
    assert attempt.finished_at is not None and attempt.correct == 5
    verdicts = [edit["text"] for edit in tg.edits if "Javobingiz" in edit["text"]]
    assert len(verdicts) == 5 and all(text.endswith("✅ To'g'ri") for text in verdicts)
    assert "5/5" in tg.last["text"]
    assert DailyTask.objects.get(kind=Kind.REVIEW).done_at is not None
    assert state() == {}


def test_review_needs_passed_quizzes(tg: FakeTelegram, world: World) -> None:
    connect(world.student)

    handle_update(press("rv"))

    assert "hali o'tilgan test yo'q" in tg.last["text"]
    assert not ReviewAttempt.objects.exists()


def test_morning_message(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    tasks(world)

    assert announce.morning() == 1

    assert "Xayrli tong" in tg.last["text"] and "Dars 2" in tg.last["text"]
