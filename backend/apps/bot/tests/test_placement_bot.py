"""Daraja testi botda: manba havolasi, ro'yxatdan o'tgach yo'nalish, vaqtli test (natija oxirida),
kupon va ariza; kursda o'qiyotganlarga — yo'q."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.catalog.models import Category, Course, Lesson, Module
from apps.leads.models import Lead
from apps.placement.models import PlacementAttempt, PlacementTest
from apps.quizzes.models import Question, Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import Layout, import_questions
from apps.rewards.models import Coupon
from apps.users.models import User
from apps.users.services import referral_code

from .conftest import (
    SOURCE,
    TG_ID,
    FakeTelegram,
    World,
    buttons,
    connect,
    contact,
    keyboard,
    make_user,
    message,
    press,
)

pytestmark = pytest.mark.django_db

STEPS = ["HTML o'qiladi", "CSS qo'llanadi", "JavaScript ishga tushadi"]
PAIRS = {"HTML": "tuzilma", "CSS": "ko'rinish", "JavaScript": "harakat"}


@pytest.fixture
def level(db: Any) -> PlacementTest:
    """«Python» yo'nalishi: 5 savol xizmat kursidagi dars testida (o'quvchilarga ko'rinmaydi)."""
    category = Category.objects.create(slug="dasturlash", name_uz="Dasturlash")
    course = Course.objects.create(
        slug="python", title_uz="Python", category=category, status=Course.Status.PUBLISHED
    )
    service = Course.objects.create(slug="daraja", title_uz="Daraja testlari", category=category)
    module = Module.objects.create(course=service, title_uz="Python")
    lesson = Lesson.objects.create(module=module, title_uz="Python: daraja testi")
    quiz = Quiz.objects.create(lesson=lesson, title="Python: daraja testi")
    import_questions(quiz, parse(SOURCE))
    return PlacementTest.objects.create(
        course=course, title="Python", quiz=quiz, questions_count=5, duration_min=15
    )


def state() -> dict[str, Any]:
    return dict(BotChat.objects.get(chat_id=TG_ID).state.get("quiz") or {})


def spot(layout: Layout, text: str, *, match: bool = False) -> int:
    values = [item.match if match else item.text for item in layout.shown]
    return values.index(text) + 1


def answer(*, right: bool = True) -> None:
    now = state()
    attempt = PlacementAttempt.objects.get(pk=now["a"])
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


def test_newcomer_from_instagram_takes_the_level_test(
    tg: FakeTelegram, level: PlacementTest, django_capture_on_commit_callbacks: Any
) -> None:
    handle_update(message("/start ig"))
    handle_update(press("lang:uz"))
    handle_update(contact("998901234567"))

    user = User.objects.get(phone="+998901234567")
    assert user.signup_source == "ig"
    registered = next(item for item in tg.messages if "Akkaunt ochildi" in item["text"])
    assert "🎯 Daraja testi" in keyboard(registered)
    offer = tg.last
    assert "Bepul daraja testi" in offer["text"] and "15% yoki 25% chegirma" in offer["text"]
    assert "72 soat" in offer["text"]
    assert [item["callback_data"] for item in buttons(offer)] == [f"pt:{level.pk}"]

    handle_update(press(f"pt:{level.pk}"))
    intro = tg.last
    assert "5 savol · 15 daqiqa" in intro["text"] and "70%" in intro["text"]
    assert buttons(intro)[0]["callback_data"] == f"pg:{level.pk}"
    assert not PlacementAttempt.objects.exists()  # vaqt «Boshlash» bilan boshlanadi

    handle_update(press(f"pg:{level.pk}"))
    assert state()["k"] == "placement" and "daqiqa qoldi" in tg.last["text"]
    for _index in range(4):
        answer()
    with django_capture_on_commit_callbacks(execute=True):
        answer(right=False)

    attempt = PlacementAttempt.objects.get()
    assert attempt.score == 80 and attempt.finished_at is not None
    everything = " ".join([*tg.texts, *(edit["text"] for edit in tg.edits)])
    assert "To'g'ri javob:" not in everything and "✅ To'g'ri" not in everything
    done = tg.last
    assert "Natijangiz: 80%" in done["text"] and "yaxshi daraja" in done["text"]
    assert "25% chegirma" in done["text"] and "Menejerimiz" in done["text"]
    assert "/api/v1/bot/login/" in buttons(done)[0]["url"]
    assert state() == {}
    coupon = Coupon.objects.get(user=user)
    assert (coupon.kind, coupon.percent) == (Coupon.Kind.PLACEMENT, 25)
    lead = Lead.objects.get()
    assert (lead.source, lead.course, lead.utm_source) == ("BOT_TEST", level.course, "ig")

    # Menyudan qayta: kupon eslatiladi, yangi kupon va'da qilinmaydi.
    handle_update(message("🎯 Daraja testi"))
    again = tg.last["text"]
    assert "Sizda <b>25% chegirma</b> kuponi bor" in again and "Bepul" not in again
    handle_update(press(f"pt:{level.pk}"))
    assert "Kupon avval berilgan" in tg.last["text"]


def test_time_is_kept_on_the_server(tg: FakeTelegram, level: PlacementTest) -> None:
    connect(make_user("+998901000009"))
    handle_update(press(f"pg:{level.pk}"))
    answer()
    PlacementAttempt.objects.update(deadline=timezone.now() - timedelta(seconds=1))

    answer()

    attempt = PlacementAttempt.objects.get()
    assert attempt.score == 20 and attempt.finished_at == attempt.deadline
    assert "Natijangiz: 20%" in tg.last["text"] and "15% chegirma" in tg.last["text"]
    assert state() == {}


def test_enrolled_student_has_no_level_test(
    tg: FakeTelegram, world: World, level: PlacementTest
) -> None:
    connect(world.student)

    handle_update(message("/start"))
    assert "🎯 Daraja testi" not in keyboard(tg.last)

    handle_update(message("🎯 Daraja testi"))
    assert "hali kursga yozilmaganlar uchun" in tg.last["text"]
    handle_update(press(f"pg:{level.pk}"))
    assert "hali kursga yozilmaganlar uchun" in tg.last["text"]
    assert not PlacementAttempt.objects.exists()


def test_newcomer_menu_has_the_level_test(tg: FakeTelegram, level: PlacementTest) -> None:
    connect(make_user("+998901000009"))

    handle_update(message("/start"))
    assert "🎯 Daraja testi" in keyboard(tg.last)

    PlacementTest.objects.update(is_active=False)
    handle_update(message("/start"))
    assert "🎯 Daraja testi" not in keyboard(tg.last)
    handle_update(press(f"pt:{level.pk}"))
    assert tg.last["text"] == "Bu test hozir mavjud emas."


def test_first_source_is_kept(tg: FakeTelegram) -> None:
    handle_update(message("/start ig"))
    handle_update(message("/start ads_2"))
    assert BotChat.objects.get(chat_id=TG_ID).source == "ig"

    friend = make_user("+998907770000", name="Do'st")
    other = {"id": 6002, "is_bot": False, "first_name": "Vali", "language_code": "uz"}
    handle_update(message(f"/start r_{referral_code(friend)}", sender=other))
    handle_update(message("/start Bad Source!", sender={**other, "id": 6003}))

    assert BotChat.objects.get(chat_id=6002).source == "ref"
    assert BotChat.objects.get(chat_id=6003).source == ""
