"""Botdagi admin panel: statistika faqat ruxsati borlarga, davr tugmalari, menyu tugmasi."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.leads.models import Lead
from apps.learning.models import LessonProgress
from apps.notifications.texts import day_month
from apps.payments.models import Order
from apps.quizzes.models import Attempt
from apps.users.models import User
from apps.users.roles import Role

from .conftest import (
    APP,
    FakeTelegram,
    World,
    buttons,
    connect,
    keyboard,
    make_user,
    message,
    press,
)

pytestmark = pytest.mark.django_db

ADMIN_BUTTON = "📊 Admin panel"


def lines_of(text: str) -> list[str]:
    return text.splitlines()


def test_admin_sees_statistics_and_switches_period(tg: FakeTelegram, world: World) -> None:
    connect(make_user("+998909000001", Role.ADMIN, name="Rahbar"))
    connect(world.student, chat_id=6001)
    BotChat.objects.create(chat_id=6002, first_name="Mehmon")
    BotChat.objects.create(chat_id=6003, blocked_at=timezone.now())
    BotChat.objects.create(chat_id=6004, news=False)
    User.objects.create_user(
        phone="+998901000003", password="x", first_name="Kichkina", audience=User.Audience.KIDS
    )
    now = timezone.now()
    LessonProgress.objects.create(user=world.student, lesson=world.lessons[0], completed_at=now)
    Attempt.objects.create(quiz=world.quiz, student=world.student, passed=True, finished_at=now)
    order = Order.objects.create(user=world.student, course=world.course, amount=1_200_000)
    Order.objects.filter(pk=order.pk).update(status=Order.Status.PAID, paid_at=now)
    lead = Lead.objects.create(name="A", phone="+998901111111")
    Lead.objects.filter(pk=lead.pk).update(created_at=now - timedelta(hours=3))

    handle_update(message("/admin"))

    lines = lines_of(tg.last["text"])
    today = day_month(timezone.localdate(), "uz")
    assert lines[0] == f"📊 <b>Admin panel</b> · Bugun, {today}"
    for line in [
        "🤖 Bot: <b>5</b> · yangi <b>+5</b>",
        "├ ro'yxatdan o'tgan: 2",
        "├ ro'yxatdan o'tmagan: 3",
        "├ botni bloklagan: 1",
        "└ yangiliklarni o'chirgan: 1",
        # O'quvchilar: Telegram'li o'quvchi va Kids; o'qituvchi va admin (xodim) hisobga kirmaydi.
        "🌐 Sayt (o'quvchilar): <b>2</b> · yangi <b>+2</b>",
        "├ Telegram ulangan: 1",
        "└ SIFAT Kids: 1",
        "├ tugatilgan darslar: <b>1</b>",
        "├ o'tilgan testlar: <b>1</b>",
        "├ o'qigan o'quvchilar: <b>1</b>",
        "├ kurs tanladi: <b>1</b>",
        "├ to'ladi: <b>1</b> — 1 200 000 so'm",
        "⚠️ <b>Muammolar</b>",
        "• 2 soatdan beri javobsiz arizalar — 1",
    ]:
        assert line in lines, line
    assert lines[-1].startswith("🕒 ") and lines[-1].endswith(" holatiga")
    found = buttons(tg.last)
    assert [(item["text"], item.get("callback_data")) for item in found[:5]] == [
        ("✅ Bugun", "ad:today"),
        ("Kecha", "ad:yesterday"),
        ("7 kun", "ad:7d"),
        ("30 kun", "ad:30d"),
        ("🔄 Yangilash", "ad:today"),
    ]
    # https saytda havolalar — inline tugma (localhost'da matnga o'tadi).
    assert [(item["text"], item["url"]) for item in found[5:]] == [
        ("🖥 Admin panel (sayt)", f"{APP}/admin/"),
        ("📣 Xabar yuborish", f"{APP}/admin/notifications/broadcast/add/"),
    ]

    sent = tg.next_id  # yuborilgan panelning message_id si
    handle_update(press("ad:7d", message_id=sent))

    [changed] = tg.edits
    assert changed["message_id"] == sent
    week = day_month(timezone.localdate() - timedelta(days=6), "uz")
    assert changed["text"].startswith(f"📊 <b>Admin panel</b> · 7 kun: {week} – {today}")
    assert "✅ 7 kun" in [item["text"] for item in buttons(changed)]
    assert tg.notices == [""]


def test_menu_has_admin_button_only_for_statistics_viewers(tg: FakeTelegram) -> None:
    connect(make_user("+998909000002", Role.MANAGER, name="Menejer"))

    handle_update(message("/menu"))

    assert keyboard(tg.last)[0] == ADMIN_BUTTON
    handle_update(message(ADMIN_BUTTON))
    assert "<b>Admin panel</b> · Bugun" in tg.last["text"]


@pytest.mark.parametrize("role", [Role.STUDENT, Role.TEACHER])
def test_others_are_refused(tg: FakeTelegram, role: str) -> None:
    connect(make_user("+998901000005", role))

    handle_update(message("/menu"))
    assert ADMIN_BUTTON not in keyboard(tg.last)

    for text in ("/admin", ADMIN_BUTTON):
        handle_update(message(text))
        assert tg.last["text"] == "⛔ Bu bo'lim faqat administratorlar uchun."
    handle_update(press("ad:today"))
    assert tg.notices[-1] == "⛔ Bu bo'lim faqat administratorlar uchun."
    assert not tg.edits


def test_without_account_admin_is_refused(tg: FakeTelegram) -> None:
    BotChat.objects.create(chat_id=5001, language="uz")

    handle_update(message("/admin"))

    assert tg.last["text"] == "⛔ Bu bo'lim faqat administratorlar uchun."
