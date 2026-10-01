"""Kabinet API: xabarlar ro'yxati, o'qilgan belgisi, sozlamalar va Telegram havolasi."""

from typing import Any

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.users.models import SocialAccount

from .conftest import make_student

pytestmark = pytest.mark.django_db


def client_for(user: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_list_shows_only_own_newest_first() -> None:
    me = make_student("+998901000001")
    other = make_student("+998901000002")
    Notification.objects.create(user=me, kind="TEST", title="Birinchi")
    Notification.objects.create(user=me, kind="TEST", title="Ikkinchi", link="/dashboard")
    Notification.objects.create(user=other, kind="TEST", title="Begona")

    body = client_for(me).get("/api/v1/notifications/").json()

    assert [item["title"] for item in body["results"]] == ["Ikkinchi", "Birinchi"]
    assert body["results"][0]["link"] == "/dashboard"


def test_read_marks_and_me_counts() -> None:
    me = make_student()
    first = Notification.objects.create(user=me, kind="TEST", title="A")
    Notification.objects.create(user=me, kind="TEST", title="B")
    client = client_for(me)

    assert client.get("/api/v1/me/").json()["unread_notifications"] == 2
    partial = client.post("/api/v1/notifications/read/", {"ids": [first.pk]}, format="json")
    everything = client.post("/api/v1/notifications/read/", {}, format="json")

    assert partial.json() == {"unread": 1}
    assert everything.json() == {"unread": 0}
    assert client.get("/api/v1/me/").json()["unread_notifications"] == 0


def test_settings_show_and_change(settings: Any) -> None:
    me = make_student(telegram_id=77)
    client = client_for(me)

    shown = client.get("/api/v1/me/notifications/").json()
    changed = client.patch(
        "/api/v1/me/notifications/",
        {"telegram_notify": False, "marketing_consent": True},
        format="json",
    ).json()

    assert shown == {
        "telegram": {"available": True, "connected": True, "notify": True, "blocked": False},
        "marketing_consent": False,
    }
    assert changed["telegram"]["notify"] is False and changed["marketing_consent"] is True
    assert not SocialAccount.objects.get(user=me).notify
    me.refresh_from_db()
    assert me.marketing_consent_at is not None

    settings.TELEGRAM_BOT_TOKEN = ""
    assert client.get("/api/v1/me/notifications/").json()["telegram"]["available"] is False


def test_connect_link(settings: Any) -> None:
    client = client_for(make_student())

    link = client.post("/api/v1/me/telegram/connect/")
    settings.TELEGRAM_BOT_TOKEN = ""
    unavailable = client.post("/api/v1/me/telegram/connect/")

    assert link.status_code == 200
    assert link.json()["url"].startswith("https://t.me/sifat_test_bot?start=c_")
    assert link.json()["expires_in"] == 600
    assert unavailable.status_code == 503


def test_connect_link_is_rate_limited() -> None:
    cache.clear()
    client = client_for(make_student())

    codes = [client.post("/api/v1/me/telegram/connect/").status_code for _ in range(11)]

    assert codes[:10] == [200] * 10 and codes[10] == 429


def test_anonymous_is_rejected() -> None:
    client = APIClient()

    assert client.get("/api/v1/notifications/").status_code == 403
    assert client.get("/api/v1/me/notifications/").status_code == 403
