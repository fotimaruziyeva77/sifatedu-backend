"""Xabar yuborish: kanal tanlash, rozilik, Telegram xatolari, SMS zaxira va takrorlanmaslik."""

import urllib.error
from typing import Any
from unittest import mock

import pytest

from apps.notifications import services, telegram
from apps.notifications.models import Delivery, Notification
from apps.notifications.tasks import deliver
from apps.users.models import SocialAccount

from .conftest import make_student

pytestmark = pytest.mark.django_db


def notify(user: Any, callbacks: Any, **kwargs: Any) -> Notification:
    kwargs.setdefault("title", "Salom")
    with callbacks(execute=True):
        notification = services.notify(user, Notification.Kind.TEST, **kwargs)
    assert notification is not None
    notification.refresh_from_db()
    return notification


def test_telegram_when_connected_otherwise_only_site(
    sent: mock.MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    linked = make_student(telegram_id=777)
    plain = make_student("+998901234568")

    first = notify(
        linked, django_capture_on_commit_callbacks, body="Ertaga dars 18:00 da", link="/dashboard"
    )
    second = notify(plain, django_capture_on_commit_callbacks)

    assert (first.telegram, first.sms) == (Delivery.SENT, "")
    assert (second.telegram, second.sms) == ("", "")
    chat_id, message = sent.call_args.args
    assert chat_id == "777"
    assert message == "<b>Salom</b>\n\nErtaga dars 18:00 da"
    button = sent.call_args.kwargs["reply_markup"]["inline_keyboard"][0][0]
    assert button == {"text": "Ochish", "url": "https://sifatedu.uz/uz/dashboard"}


def test_local_link_goes_into_text(
    settings: Any, sent: mock.MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    # Telegram tugmada http://localhost havolasini qabul qilmaydi.
    settings.APP_URL = "http://localhost"
    user = make_student(telegram_id=777, locale="ru")

    notify(user, django_capture_on_commit_callbacks, link="/dashboard/courses")

    assert sent.call_args.kwargs["reply_markup"] is None
    assert sent.call_args.args[1].endswith("http://localhost/ru/dashboard/courses")


def test_promo_needs_consent() -> None:
    without = make_student(telegram_id=1)
    agreed = make_student("+998901234568", telegram_id=2, consent=True)
    account = {user.pk: SocialAccount.objects.get(user=user) for user in (without, agreed)}

    cold = services.build(
        without,
        "BROADCAST",
        title="Chegirma",
        sms_text="SMS",
        promo=True,
        account=account[without.pk],
    )
    warm = services.build(
        agreed,
        "BROADCAST",
        title="Chegirma",
        sms_text="SMS",
        promo=True,
        account=account[agreed.pk],
    )

    assert (cold.telegram, cold.sms, cold.sms_text) == ("", "", "")
    assert (warm.telegram, warm.sms) == (Delivery.QUEUED, "")


def test_sms_when_no_telegram(django_capture_on_commit_callbacks: Any) -> None:
    user = make_student()

    with mock.patch.object(services, "send_sms") as sms:
        result = notify(user, django_capture_on_commit_callbacks, sms_text="To'lov qabul qilindi")

    assert (result.telegram, result.sms) == ("", Delivery.SENT)
    sms.assert_called_once_with(user.phone, "To'lov qabul qilindi")


def test_blocked_bot_is_remembered_and_sms_takes_over(
    sent: mock.MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    user = make_student(telegram_id=777)
    sent.side_effect = telegram.TelegramError(403, "Forbidden: bot was blocked by the user")

    with mock.patch.object(services, "send_sms") as sms:
        result = notify(user, django_capture_on_commit_callbacks, sms_text="Matn")

    assert (result.telegram, result.sms) == (Delivery.FAILED, Delivery.SENT)
    assert "blocked" in result.error
    sms.assert_called_once()
    assert SocialAccount.objects.get(user=user).blocked_at is not None

    # Keyingi xabar Telegram'ga urinmaydi.
    sent.reset_mock()
    later = notify(user, django_capture_on_commit_callbacks)
    assert later.telegram == "" and not sent.called


def test_user_can_turn_telegram_off(
    sent: mock.MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    user = make_student(telegram_id=777)
    SocialAccount.objects.filter(user=user).update(notify=False)

    result = notify(user, django_capture_on_commit_callbacks)

    assert result.telegram == "" and not sent.called


def test_rate_limit_retries_and_skips_already_sent(sent: mock.MagicMock) -> None:
    first = services.build(make_student(telegram_id=1), "TEST", title="A", account=None)
    first.telegram = Delivery.QUEUED
    first.save()
    second = services.build(make_student("+998901234568", telegram_id=2), "TEST", title="B")
    second.telegram = Delivery.QUEUED
    second.save()
    # Birinchisi ketadi, ikkinchisida 429 — qayta urinishda faqat ikkinchisi yuboriladi.
    sent.side_effect = [None, telegram.TelegramError(429, "Too Many Requests", 1), None]

    deliver.apply(args=([first.pk, second.pk],))

    assert sent.call_count == 3
    assert [call.args[0] for call in sent.call_args_list] == ["1", "2", "2"]
    assert set(Notification.objects.values_list("telegram", flat=True)) == {Delivery.SENT}


def test_network_failure_gives_up_after_retries(sent: mock.MagicMock) -> None:
    notification = services.build(make_student(telegram_id=1), "TEST", title="A")
    notification.telegram = Delivery.QUEUED
    notification.save()
    sent.side_effect = urllib.error.URLError("timeout")

    deliver.apply(args=([notification.pk],))

    notification.refresh_from_db()
    assert notification.telegram == Delivery.FAILED
    assert notification.error == "tarmoq xatosi"


def test_dedupe_key_sends_once(
    sent: mock.MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    user = make_student(telegram_id=777)

    with django_capture_on_commit_callbacks(execute=True):
        first = services.notify(user, "TEST", title="A", dedupe_key="once:1")
        again = services.notify(user, "TEST", title="A", dedupe_key="once:1")

    assert first is not None and again is None
    assert Notification.objects.count() == 1 and sent.call_count == 1


def test_sms_parts() -> None:
    assert services.sms_parts("") == 0
    assert services.sms_parts("a" * 160) == 1
    assert services.sms_parts("a" * 161) == 2
    assert services.sms_parts("я" * 71) == 2
