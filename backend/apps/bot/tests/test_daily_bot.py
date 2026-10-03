"""Kunlik test botda: «📝 Testlar» va ertalabki xabar tugmasi, savollar (javobda baho yo'q),
oxirida to'g'ri / noto'g'ri soni va XP, guruh reytingi, javoblar — test yopilgach."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.dailytest import services
from apps.dailytest.models import DailyAttempt, DailyTest
from apps.dailytest.tests.conftest import bank
from apps.live.models import GroupLesson
from apps.notifications.models import Notification
from apps.notifications.services import telegram_message
from apps.quizzes.models import Question
from apps.quizzes.services import Layout

from .conftest import TG_ID, FakeTelegram, World, buttons, connect, message, press

pytestmark = pytest.mark.django_db


@pytest.fixture
def daily(world: World) -> DailyTest:
    """Guruhda o'tilgan dars (20 savol) va hozir ochiq kunlik test."""
    bank(world.lessons[1], 20)
    GroupLesson.objects.create(group=world.group, lesson=world.lessons[1], opened_by=world.teacher)
    now = timezone.now()
    return DailyTest.objects.create(
        group=world.group,
        day=services.local_day(now),
        questions_count=20,
        pool_size=20,
        opens_at=now - timedelta(hours=1),
        closes_at=now + timedelta(hours=2),
    )


def state() -> dict[str, Any]:
    return dict(BotChat.objects.get(chat_id=TG_ID).state.get("quiz") or {})


def answer(*, right: bool) -> None:
    now = state()
    attempt = DailyAttempt.objects.get(pk=now["a"])
    question = Question.objects.prefetch_related("choices").get(pk=now["q"])
    layout = Layout.build(question, attempt.seed)
    position = [choice.is_correct for choice in layout.shown].index(right) + 1
    handle_update(press(f"qa:{attempt.pk}:{question.pk}:{position}"))


def test_daily_test_in_bot(tg: FakeTelegram, world: World, daily: DailyTest) -> None:
    connect(world.student)

    handle_update(message("📝 Testlar"))
    menu = tg.last
    assert "Kunlik test</b>: 20 savol" in menu["text"]
    assert buttons(menu)[0]["callback_data"] == "dq"

    handle_update(press("dq"))
    intro = tg.last
    assert "20 savol" in intro["text"] and "+2 XP va +1 coin" in intro["text"]
    assert buttons(intro)[0]["callback_data"] == f"dg:{daily.pk}"
    assert not DailyAttempt.objects.exists()  # «Boshlash» bosilmaguncha urinish yo'q

    handle_update(press(f"dg:{daily.pk}"))
    assert state()["k"] == "daily"
    for index in range(20):
        answer(right=index < 18)

    attempt = DailyAttempt.objects.get()
    assert (attempt.correct, attempt.total) == (18, 20) and attempt.finished_at is not None
    everything = " ".join([*tg.texts, *(edit["text"] for edit in tg.edits)])
    assert "✅ To'g'ri" not in everything and "To'g'ri javob:" not in everything
    done = tg.last
    assert "To'g'ri: <b>18</b> · Noto'g'ri: <b>2</b>" in done["text"]
    assert "+36 XP, +18 coin" in done["text"] and "1-o'rin (1 kishidan)" in done["text"]
    assert [item["callback_data"] for item in buttons(done)] == [f"dr:{daily.pk}"]
    assert state() == {}

    handle_update(press(f"dr:{daily.pk}"))
    assert "kunlik test reytingi" in tg.last["text"] and "Aziz — 18/20 ←" in tg.last["text"]
    handle_update(press(f"dv:{attempt.pk}"))
    assert "test yopilgach" in tg.last["text"]

    handle_update(message("📝 Testlar"))
    assert "Kunlik test: <b>18/20</b> ✅" in tg.last["text"]
    handle_update(press("dq"))
    assert "ishlagansiz: <b>18/20</b>" in tg.last["text"]


def test_answers_after_closing(tg: FakeTelegram, world: World, daily: DailyTest) -> None:
    connect(world.student)
    attempt = services.start(daily, world.student)
    handle_update(press("dq"))  # boshlangan test davom etadi
    for index in range(20):
        answer(right=index != 3)
    DailyTest.objects.filter(pk=daily.pk).update(closes_at=timezone.now() - timedelta(minutes=1))

    handle_update(press(f"dv:{attempt.pk}"))

    review = tg.last["text"]
    assert "Xatolar ustida ishlash" in review and "To'g'ri javob:" in review
    assert review.count("❌") == 1


def test_morning_message_button_and_start_link(
    tg: FakeTelegram, world: World, daily: DailyTest
) -> None:
    connect(world.student)
    note = Notification(
        user=world.student,
        kind=Notification.Kind.DAILY_TEST,
        title="📝 Kunlik test ochildi",
        link=services.LINK,
    )
    _text, markup = telegram_message(note)
    assert markup is not None and markup["inline_keyboard"][0][0]["callback_data"] == "dq"

    handle_update(message("/start dt"))

    assert buttons(tg.last)[0]["callback_data"] == f"dg:{daily.pk}"
    assert BotChat.objects.get(chat_id=TG_ID).source == ""  # "dt" — reklama manbasi emas


def test_without_a_test_today(tg: FakeTelegram, world: World) -> None:
    connect(world.student)

    handle_update(press("dq"))

    assert "Bugun kunlik test yo'q" in tg.last["text"]
