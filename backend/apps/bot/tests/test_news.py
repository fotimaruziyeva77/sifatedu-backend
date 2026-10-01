"""Yangiliklar "Botdagi hammaga": ro'yxatdan o'tmaganlarga ham, har kimga bir marta."""

import base64
from datetime import datetime
from typing import Any
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.catalog.models import Category, Course
from apps.notifications import services
from apps.notifications.admin import BroadcastForm
from apps.notifications.models import Broadcast, Delivery, Notification
from apps.users.models import SocialAccount
from apps.users.roles import Role

from .conftest import TG_ID, FakeTelegram, buttons, connect, make_user, press

pytestmark = pytest.mark.django_db

TASHKENT = ZoneInfo("Asia/Tashkent")
# 1×1 PNG.
PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="
)


def news(**fields: Any) -> Broadcast:
    return Broadcast.objects.create(
        title="Yangi kurs: Python",
        body="1-oktabrdan qabul boshlanadi.",
        link="/courses",
        bot_all=True,
        **fields,
    )


def send(message: Broadcast, capture: Any) -> None:
    admin = make_user("+998900000009", Role.ADMIN, name="Admin")
    noon = datetime(2026, 9, 30, 12, 0, tzinfo=TASHKENT)
    with mock.patch.object(services.timezone, "now", return_value=noon), capture(execute=True):
        assert services.schedule(message, admin) is None


def test_bot_subscribers_get_news_once(
    tg: FakeTelegram, django_capture_on_commit_callbacks: Any
) -> None:
    student = make_user("+998901000001", Role.STUDENT)
    connect(student, chat_id=7001)
    muted = make_user("+998901000002", Role.STUDENT)
    connect(muted, chat_id=7002)
    SocialAccount.objects.filter(user=muted).update(notify=False)
    BotChat.objects.create(chat_id=7003, language="ru")  # ro'yxatdan o'tmagan
    BotChat.objects.create(chat_id=7004, news=False)
    BotChat.objects.create(chat_id=7005, blocked_at="2026-09-01T10:00:00+05:00")
    message = news()

    send(message, django_capture_on_commit_callbacks)

    by_chat: dict[int, list[dict[str, Any]]] = {}
    for item in tg.messages:
        by_chat.setdefault(int(item["chat_id"]), []).append(item)
    assert sorted(by_chat) == [7001, 7003]
    [guest] = by_chat[7003]
    assert guest["text"].startswith("<b>Yangi kurs: Python</b>")
    assert [item["text"] for item in buttons(guest)] == ["Открыть", "🔕 Выключить новости"]
    assert buttons(guest)[0]["url"] == "https://sifatedu.uz/ru/courses"
    message.refresh_from_db()
    assert (message.recipients, message.bot_recipients, message.bot_sent) == (2, 1, 1)
    assert Notification.objects.get(user=student).telegram == Delivery.SENT


def test_news_with_image_is_uploaded_once(
    tg: FakeTelegram, django_capture_on_commit_callbacks: Any
) -> None:
    BotChat.objects.create(chat_id=7003)
    BotChat.objects.create(chat_id=7004)
    message = news(image=SimpleUploadedFile("python.png", PIXEL, content_type="image/png"))

    send(message, django_capture_on_commit_callbacks)

    first, second = tg.of("sendPhoto")
    assert first["caption"].startswith("<b>Yangi kurs: Python</b>")
    [upload] = tg.uploads
    assert upload["files"]["photo"][0].endswith(".png")
    assert second["photo"] == "photo-file-id"
    assert not tg.messages


def test_mute_button_turns_news_off(tg: FakeTelegram) -> None:
    BotChat.objects.create(chat_id=TG_ID, language="uz")

    handle_update(press("mute"))

    assert BotChat.objects.get(chat_id=TG_ID).news is False
    assert "Yangiliklar o'chirildi" in tg.notices[-1]


def test_bot_news_waits_for_morning(tg: FakeTelegram) -> None:
    admin = make_user("+998900000009", Role.ADMIN, name="Admin")
    night = datetime(2026, 9, 29, 23, 15, tzinfo=TASHKENT)
    message = news()

    with mock.patch.object(services.timezone, "now", return_value=night):
        later = services.schedule(message, admin)

    assert later == datetime(2026, 9, 30, 9, 0, tzinfo=TASHKENT)


def test_reach_counts_extra_bot_subscribers(tg: FakeTelegram) -> None:
    connect(make_user("+998901000001", Role.STUDENT), chat_id=7001)
    BotChat.objects.create(chat_id=7003)
    BotChat.objects.create(chat_id=7004)

    reach = services.reach(news())

    assert (reach.total, reach.telegram, reach.bot) == (1, 1, 2)


def test_bot_news_must_be_unfiltered(db: Any) -> None:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="python", title_uz="Python", category=category)
    base = {"title": "Aksiya", "body": "Matn", "kind": "PROMO", "audience": "ALL", "bot_all": True}

    filtered = BroadcastForm(data={**base, "send_telegram": True, "courses": [course.pk]})
    silent = BroadcastForm(data=base)
    fine = BroadcastForm(data={**base, "send_telegram": True})

    assert "bot_all" in filtered.errors and "bot_all" in silent.errors
    assert fine.is_valid(), fine.errors
