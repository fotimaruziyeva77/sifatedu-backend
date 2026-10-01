"""Oylik imtihon testi botda: natija aytilmaydi, vaqt serverda, urinish sayt bilan umumiy."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.exams import services as exams
from apps.exams.models import Exam, ExamAttempt, ExamTask
from apps.quizzes.models import Question
from apps.quizzes.services import Layout

from .conftest import TG_ID, FakeTelegram, World, buttons, connect, message, press

pytestmark = pytest.mark.django_db

STEPS = ["HTML o'qiladi", "CSS qo'llanadi", "JavaScript ishga tushadi"]
PAIRS = {"HTML": "tuzilma", "CSS": "ko'rinish", "JavaScript": "harakat"}


@pytest.fixture
def exam(world: World) -> Exam:
    now = timezone.now()
    created = Exam.objects.create(
        course=world.course,
        month=exams.month_start(timezone.localdate()),
        status=Exam.Status.READY,
        questions_count=5,
        duration_min=30,
        opens_at=now - timedelta(hours=1),
        closes_at=now + timedelta(days=1),
    )
    ExamTask.objects.create(exam=created, order=1, title="Sahifa", instructions="Yarating")
    return created


def state() -> dict[str, Any]:
    return dict(BotChat.objects.get(chat_id=TG_ID).state.get("quiz") or {})


def spot(layout: Layout, text: str, *, match: bool = False) -> int:
    values = [item.match if match else item.text for item in layout.shown]
    return values.index(text) + 1


def answer(*, right: bool = True) -> None:
    now = state()
    attempt = ExamAttempt.objects.get(pk=now["a"])
    question = Question.objects.get(pk=now["q"])
    layout = Layout.build(question, attempt.seed)
    ref = f"{attempt.pk}:{question.pk}"
    kind = question.kind
    if kind == Question.Kind.SINGLE:
        text = "HyperText Markup Language" if right else "High Tech Modern Language"
        handle_update(press(f"qa:{ref}:{spot(layout, text)}"))
    elif kind == Question.Kind.MULTIPLE:
        for text in ["<div>", "<p>"] if right else ["<div>"]:
            handle_update(press(f"qt:{ref}:{spot(layout, text)}"))
        handle_update(press(f"qd:{ref}"))
    elif kind == Question.Kind.TEXT:
        handle_update(message("h1" if right else "h2"))
    elif kind == Question.Kind.ORDER:
        for text in STEPS if right else list(reversed(STEPS)):
            handle_update(press(f"qo:{ref}:{spot(layout, text)}"))
    else:
        rights = [PAIRS[item.text] for item in layout.choices]
        if not right:
            rights[0], rights[1] = rights[1], rights[0]
        for text in rights:
            handle_update(press(f"qm:{ref}:{spot(layout, text, match=True)}"))


def test_exam_in_bot_without_verdicts(tg: FakeTelegram, world: World, exam: Exam) -> None:
    connect(world.student)

    handle_update(message("📝 Testlar"))
    menu = tg.last
    assert "Oylik imtihon ochiq" in menu["text"]
    assert buttons(menu)[0]["callback_data"] == f"xs:{exam.pk}"

    handle_update(press(f"xs:{exam.pk}"))
    intro = tg.last
    assert "5 savol" in intro["text"] and "30 daqiqa" in intro["text"]
    start, tasks = buttons(intro)
    assert start["callback_data"] == f"xg:{exam.pk}" and "/api/v1/bot/login/" in tasks["url"]
    assert not ExamAttempt.objects.exists()  # vaqt "Boshlash" bilan boshlanadi

    handle_update(press(f"xg:{exam.pk}"))
    assert state()["k"] == "exam" and "daqiqa qoldi" in tg.last["text"]
    for index in range(5):
        answer(right=index > 0)

    attempt = ExamAttempt.objects.get()
    assert attempt.finished_at is not None and attempt.score == 80
    saved = [edit["text"] for edit in tg.edits if "Javob saqlandi" in edit["text"]]
    assert len(saved) == 5
    everything = " ".join([*tg.texts, *(edit["text"] for edit in tg.edits)])
    assert "To'g'ri javob:" not in everything and "Noto'g'ri" not in everything
    assert "✅ To'g'ri" not in everything
    done = tg.last
    assert "Test qismi yakunlandi" in done["text"] and "80%" in done["text"]
    assert "/api/v1/bot/login/" in buttons(done)[0]["url"]
    assert state() == {}

    # Qayta bosilsa — bitta urinish.
    handle_update(press(f"xs:{exam.pk}"))
    assert "topshirgansiz: 80%" in tg.last["text"]


def test_attempt_started_on_the_site_continues_in_bot(
    tg: FakeTelegram, world: World, exam: Exam
) -> None:
    connect(world.student)
    attempt = exams.start_test(exam, world.student)

    handle_update(press(f"xs:{exam.pk}"))

    assert state()["a"] == attempt.pk and "daqiqa qoldi" in tg.last["text"]


def test_time_is_over_in_bot(tg: FakeTelegram, world: World, exam: Exam) -> None:
    connect(world.student)
    handle_update(press(f"xs:{exam.pk}"))
    handle_update(press(f"xg:{exam.pk}"))
    ExamAttempt.objects.update(deadline=timezone.now() - timedelta(seconds=1))

    answer()

    attempt = ExamAttempt.objects.get()
    assert attempt.finished_at is not None and attempt.score == 0
    assert "Test qismi yakunlandi" in tg.last["text"]


def test_closed_exam_in_bot(tg: FakeTelegram, world: World, exam: Exam) -> None:
    connect(world.student)
    Exam.objects.filter(pk=exam.pk).update(closes_at=timezone.now() - timedelta(minutes=1))

    handle_update(press(f"xs:{exam.pk}"))

    assert tg.last["text"] == "Imtihon hozir ochiq emas."
    handle_update(message("📝 Testlar"))
    assert "Oylik imtihon" not in tg.last["text"]
