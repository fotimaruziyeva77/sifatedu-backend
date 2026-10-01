"""Admin bosh sahifasidagi statistika (kim ko'radi) va kunlik Telegram hisobot."""

from typing import Any
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.bot.models import BotChat
from apps.leads.models import Lead
from apps.notifications import telegram
from apps.stats import metrics, report
from apps.users.models import SocialAccount, User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db


def staff(phone: str, role: str, telegram_id: int | None = None) -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name="Xodim")
    set_roles(user, [role])
    if telegram_id is not None:
        SocialAccount.objects.create(
            user=user, provider=SocialAccount.Provider.TELEGRAM, uid=str(telegram_id)
        )
    return user


def open_index(user: User, **params: str) -> Any:
    client = Client()
    client.force_login(user)
    return client.get(reverse("admin:index"), params)


@pytest.mark.parametrize("role", [Role.DIRECTOR, Role.MANAGER, Role.ADMIN])
def test_leaders_see_statistics(role: str) -> None:
    User.objects.create_user(phone="+998901000001", password="x", first_name="Yangi")

    page = open_index(staff("+998909000001", role), period="7d")

    assert page.status_code == 200
    stats = page.context["stats"]
    assert stats["period"].key == "7d"
    assert stats["cards"][0]["value"] == 1
    html = page.content.decode()
    assert "Statistika" in html and "Qo'ng'iroq qilish kerak" in html
    assert "admin/dashboard.css" in html


def test_dashboard_counts_users_and_bot() -> None:
    student = User.objects.create_user(phone="+998901000001", password="x", first_name="Yangi")
    SocialAccount.objects.create(user=student, provider=SocialAccount.Provider.TELEGRAM, uid="7001")
    BotChat.objects.create(chat_id=7001)
    BotChat.objects.create(chat_id=7002, blocked_at=timezone.now())

    stats = open_index(staff("+998909000001", Role.ADMIN)).context["stats"]

    assert stats["cards"][0]["note"] == "Jami: 1 · Kids: 0 · Telegram orqali: 1"
    bot = stats["cards"][-1]
    assert (bot["title"], bot["value"], bot["url"]) == (
        "Botga qo'shildi",
        2,
        "/admin/bot/botchat/",
    )
    assert bot["note"] == "Jami: 2 · ro'yxatdan o'tmagan: 1 · bloklagan: 1"


def test_teacher_sees_regular_index() -> None:
    page = open_index(staff("+998909000002", Role.TEACHER))

    assert page.status_code == 200
    assert "stats" not in page.context


def test_report_text_and_recipients(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    settings.TELEGRAM_REPORTS_CHAT_ID = "-100500"
    settings.APP_URL = "https://sifatedu.uz"
    director = staff("+998909000003", Role.DIRECTOR, telegram_id=31)
    staff("+998909000004", Role.MANAGER, telegram_id=32)  # menejerga hisobot bormaydi
    staff("+998909000005", Role.ADMIN)  # Telegram ulanmagan
    User.objects.create_user(phone="+998901000002", password="x")
    Lead.objects.create(name="A", phone="+998901111111")

    with mock.patch.object(telegram, "send_message") as sent:
        count = report.send_daily_report()

    assert count == 2
    assert [call.args[0] for call in sent.call_args_list] == ["31", "-100500"]
    text = sent.call_args.args[1]
    assert "Ro'yxatdan o'tdi: <b>1</b>" in text
    assert "Arizalar: <b>1</b>" in text
    assert "https://sifatedu.uz/admin/" in text
    assert director.social_accounts.get().blocked_at is None


def test_report_marks_blocked_director(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    director = staff("+998909000006", Role.DIRECTOR, telegram_id=41)

    with mock.patch.object(
        telegram, "send_message", side_effect=telegram.TelegramError(403, "Forbidden")
    ):
        assert report.send_daily_report() == 0

    assert director.social_accounts.get().blocked_at is not None


def test_report_without_bot_is_skipped(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = ""

    assert report.send_daily_report() == 0
    assert "Muammo yo'q" in report.render(metrics.period("today"))
