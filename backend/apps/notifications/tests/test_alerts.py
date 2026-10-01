"""Jamoaga ogohlantirishlar: takrorlanishdan himoya va sozlanmagan holat."""

from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.notifications.alerts import alert


@pytest.fixture(autouse=True)
def clean_cache() -> None:
    cache.clear()


@pytest.fixture
def telegram(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = "123:abc"
    settings.TELEGRAM_ALERTS_CHAT_ID = "-100500"


@pytest.mark.usefixtures("telegram")
def test_alert_is_sent_once_per_cooldown() -> None:
    with patch("apps.notifications.tasks.send_alert_task.delay") as send:
        assert alert("click:prepare:-1", "Imzo xato") is True
        assert alert("click:prepare:-1", "Imzo xato") is False

    send.assert_called_once()


@pytest.mark.usefixtures("telegram")
def test_different_kinds_are_not_merged() -> None:
    with patch("apps.notifications.tasks.send_alert_task.delay") as send:
        alert("video:failed:1", "Birinchi video")
        alert("video:failed:2", "Ikkinchi video")

    assert send.call_count == 2


@pytest.mark.usefixtures("telegram")
def test_text_is_escaped_for_html() -> None:
    with patch("apps.notifications.tasks.send_alert_task.delay") as send:
        alert("video:failed:1", "<b>soxta</b> & belgi")

    text = send.call_args.args[0]
    assert "&lt;b&gt;soxta&lt;/b&gt; &amp; belgi" in text


def test_without_telegram_nothing_is_queued(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = ""
    with patch("apps.notifications.tasks.send_alert_task.delay") as send:
        assert alert("click:complete:internal", "Xato") is False

    send.assert_not_called()
