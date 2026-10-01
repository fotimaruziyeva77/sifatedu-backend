"""Server resurslari: disk va xotira chegarasi, Telegram ogohlantirish va admin muammosi."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.core import resources
from apps.core.tasks import check_server_resources
from apps.stats import metrics

MEMINFO = "MemTotal:        8000000 kB\nMemFree:          100000 kB\nMemAvailable:     {free} kB\n"


@pytest.fixture(autouse=True)
def clean_cache() -> Any:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def server(settings: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Disk 90% band, bo'sh xotira 5% — ikkalasi ham chegaradan oshgan."""
    settings.RESOURCE_CHECKS = True
    settings.TELEGRAM_BOT_TOKEN = "123:abc"
    settings.TELEGRAM_ALERTS_CHAT_ID = "-100500"
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(MEMINFO.format(free=400000))
    monkeypatch.setattr(resources, "MEMINFO", meminfo)
    monkeypatch.setattr(
        resources.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=100, used=90, free=10),
    )
    return meminfo


def test_memory_is_read_from_meminfo(tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(MEMINFO.format(free=2000000))

    assert resources.memory_free_percent(meminfo) == 25
    assert resources.memory_free_percent(tmp_path / "yo'q") is None


def test_alerts_once_per_cooldown(server: Path) -> None:
    with patch("apps.notifications.tasks.send_alert_task.delay") as send:
        assert check_server_resources() == ["server:disk", "server:memory"]
        check_server_resources()

    texts = [call.args[0] for call in send.call_args_list]
    assert len(texts) == 2
    # Matn HTML uchun ekranlanadi (apostrof — &#x27;), shuning uchun apostrofsiz qismi tekshiriladi.
    assert "Server diski 90% band" in texts[0] and "xotira 5% qoldi" in texts[1]


@pytest.mark.django_db
def test_disk_is_an_admin_problem(server: Path) -> None:
    found = {problem.title: problem.count for problem in metrics.problems(metrics.period("today"))}

    assert found["Server diski to'lmoqda (band, %)"] == 90


def test_normal_server_and_disabled_checks(settings: Any, server: Path) -> None:
    server.write_text(MEMINFO.format(free=4000000))
    with patch.object(
        resources.shutil, "disk_usage", lambda path: SimpleNamespace(total=100, used=40, free=60)
    ):
        assert resources.warnings() == []

    settings.RESOURCE_CHECKS = False
    assert resources.warnings() == [] and resources.disk_over_limit() == 0
