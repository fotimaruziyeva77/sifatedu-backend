"""Bot menyusi: kurslarim, jadval, do'stni taklif qilish, sozlamalar va AI maslahatchi."""

from datetime import timedelta
from typing import Any
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from django.utils import timezone

from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.live.models import LiveLesson
from apps.rewards.models import GameSettings
from apps.users.models import User

from .conftest import APP, TG_ID, FakeTelegram, World, buttons, connect, make_user, message, press

pytestmark = pytest.mark.django_db


def next_of(url: str) -> str:
    return parse_qs(urlparse(url).query)["next"][0]


def test_courses_show_progress_and_open_the_site(tg: FakeTelegram, world: World) -> None:
    connect(world.student)

    handle_update(message("📚 Kurslarim"))

    text = tg.last["text"]
    assert "<b>Frontend</b> — 0% (0/3)" in text and "Keyingi dars: Dars 1" in text
    [course] = buttons(tg.last)
    assert course["text"] == "▶️ Frontend"
    assert course["url"].startswith(f"{APP}/api/v1/bot/login/")
    assert next_of(course["url"]) == f"/dashboard/courses/frontend/lessons/{world.lessons[0].pk}"


def test_no_courses_points_to_catalog(tg: FakeTelegram) -> None:
    connect(make_user("+998901112233"))

    handle_update(message("/courses"))

    assert "Sizda hali kurs yo'q" in tg.last["text"]
    assert buttons(tg.last)[0]["url"] == f"{APP}/uz/courses"


def test_schedule_offers_join_only_when_open(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    now = timezone.now()
    live_now = LiveLesson.objects.create(
        group=world.group,
        starts_at=now - timedelta(minutes=5),
        duration_min=90,
        meet_url="https://meet.google.com/abc-defg-hij",
        title="Flexbox",
    )
    LiveLesson.objects.create(
        group=world.group,
        starts_at=now + timedelta(days=2),
        duration_min=90,
        meet_url="https://meet.google.com/abc-defg-hij",
    )

    handle_update(message("📅 Jadval"))

    text = tg.last["text"]
    assert "Yaqin darslar" in text and "Frontend · FE-1 · onlayn" in text
    assert "Mavzu: Flexbox" in text
    assert "15 daqiqa oldin chiqadi" in text
    [join] = buttons(tg.last)
    assert join["text"].startswith("🔗 Qo'shilish")
    assert next_of(join["url"]) == f"/api/v1/live/{live_now.pk}/join/"


def test_schedule_without_group(tg: FakeTelegram) -> None:
    connect(make_user("+998901112233"))

    handle_update(message("/schedule"))

    assert "guruhga qo'shilmagansiz" in tg.last["text"]


def test_invite_gives_personal_links_and_counts_friends(tg: FakeTelegram) -> None:
    user = make_user("+998901112233")
    connect(user)

    handle_update(message("🎁 Do'stni taklif qilish"))

    user.refresh_from_db()
    code = user.referral_code
    assert code and len(code) == 8
    text = tg.last["text"]
    assert f"https://t.me/sifat_test_bot?start=r_{code}" in text
    assert f"{APP}/uz?ref={code}" in text
    assert "Taklif qilganlaringiz: <b>0</b>" in text
    [share] = buttons(tg.last)
    assert share["url"].startswith("https://t.me/share/url?")

    friend = make_user("+998901112244")
    friend.referred_by = user
    friend.save(update_fields=["referred_by"])
    handle_update(message("🎁 Do'stni taklif qilish"))
    assert "Taklif qilganlaringiz: <b>1</b>" in tg.last["text"]
    # Kod bir marta yaratiladi va o'zgarmaydi.
    assert User.objects.get(pk=user.pk).referral_code == code


def test_invite_lists_rewards_from_game_settings(tg: FakeTelegram) -> None:
    connect(make_user("+998901112233"))

    handle_update(message("/invite"))

    lines = tg.last["text"].splitlines()
    assert lines[-4:] == [
        "<b>Mukofotlar</b>",
        "🪙 Do'stingiz birinchi darsni tugatsa — <b>+50 coin</b>",
        "💳 Do'stingiz to'lov qilsa — <b>+100 coin va 10% kupon</b>",
        "🎉 Do'stingizga birinchi to'lovda <b>10% chegirma</b>",
    ]

    config = GameSettings.load()
    config.referral_lesson_coins = 0
    config.coupon_percent = 0
    config.save()
    handle_update(message("/invite"))

    text = tg.last["text"]
    assert "💳 Do'stingiz to'lov qilsa — <b>+100 coin</b>" in text
    assert "birinchi darsni" not in text and "kupon" not in text


def test_settings_toggle_news_and_change_language(tg: FakeTelegram, world: World) -> None:
    connect(world.student)

    handle_update(message("⚙️ Sozlamalar"))
    settings = tg.last
    assert "Yangiliklar: yoqilgan ✅" in settings["text"]
    labels = [item["text"] for item in buttons(settings)]
    assert labels == ["🌐 Tilni o'zgartirish", "🔕 Yangiliklarni o'chirish", "🖥 Saytga kirish"]

    handle_update(press("news"))
    assert BotChat.objects.get(chat_id=TG_ID).news is False
    assert "Yangiliklar: o'chirilgan" in tg.edits[-1]["text"]
    assert "Yangiliklar o'chirildi" in tg.notices[-1]

    handle_update(press("lang"))
    handle_update(press("lang:ru"))
    assert BotChat.objects.get(chat_id=TG_ID).language == "ru"
    assert "С возвращением, Aziz" in tg.last["text"]


def test_free_text_goes_to_ai_advisor(
    tg: FakeTelegram, world: World, django_capture_on_commit_callbacks: Any
) -> None:
    connect(world.student)

    with (
        mock.patch("apps.assistant.tasks.telegram_answer.delay") as ask,
        django_capture_on_commit_callbacks(execute=True),
    ):
        handle_update(message("Backend kursi qancha davom etadi?"))

    ask.assert_called_once_with(
        TG_ID,
        {"first_name": "Aziz", "last_name": "", "username": "aziz"},
        "Backend kursi qancha davom etadi?",
        "uz",
    )


def test_ai_answer_keeps_menu_keyboard(tg: FakeTelegram, settings: Any) -> None:
    from apps.assistant import telegram as advisor

    settings.ASSISTANT_DRY_RUN = True
    connect(make_user("+998901112233"))

    advisor.answer(TG_ID, {"first_name": "Aziz"}, "Qanday kurslar bor?", "uz")

    reply = tg.last
    assert reply["chat_id"] == TG_ID and reply["text"].startswith("🧪 Test rejimi")
    assert "reply_markup" not in reply


def test_non_text_message(tg: FakeTelegram, world: World) -> None:
    connect(world.student)

    handle_update(message(photo=[{"file_id": "x"}]))

    assert "faqat matnli xabarlarni" in tg.last["text"]
