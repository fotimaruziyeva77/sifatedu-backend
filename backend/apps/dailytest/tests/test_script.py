"""scripts/kunlik_test.py: bugungi testni qo'lda, hozir yuborish (07:00 o'tib ketgan bo'lsa)."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from django.conf import settings
from django.utils import timezone

from apps.dailytest import services
from apps.dailytest.models import DailyTest
from apps.learning.models import Enrollment
from apps.live.models import GroupLesson
from apps.notifications.models import Notification
from apps.users.roles import Role

from .conftest import World, at, make_user

pytestmark = pytest.mark.django_db

SCRIPT = Path(settings.BASE_DIR) / "scripts" / "kunlik_test.py"


def run(action: str, moment: datetime) -> None:
    """Skript serverdagidek: Django shell'ga uzatilgan kod, ACTION muhit o'zgaruvchisida."""
    code = compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec")
    with (
        mock.patch.dict(os.environ, {"ACTION": action}),
        mock.patch.object(timezone, "now", return_value=moment),
    ):
        exec(code, {"__name__": "kunlik_test"})  # noqa: S102 — serverda ham shunday ishlaydi


def announced() -> list[str]:
    return sorted(
        Notification.objects.filter(kind=Notification.Kind.DAILY_TEST).values_list(
            "user__first_name", flat=True
        )
    )


def test_send_opens_the_morning_skipped_test_once_bank_is_ready(world: World, capsys: Any) -> None:
    covered = list(
        GroupLesson.objects.filter(group=world.group).values_list("lesson_id", flat=True)
    )
    GroupLesson.objects.filter(group=world.group).delete()
    assert services.open_day(now=at(7)) == 0  # ertalab bank bo'sh — test berilmadi
    test = DailyTest.objects.get(group=world.group)
    assert test.status == DailyTest.Status.SKIPPED
    for lesson_id in covered:
        GroupLesson.objects.create(group=world.group, lesson_id=lesson_id, opened_by=world.teacher)

    run("send", at(10))
    run("send", at(10, 5))  # qayta — hech kimga ikkinchi marta bormaydi

    test.refresh_from_db()
    assert (test.status, test.pool_size) == (DailyTest.Status.OPEN, 24)
    assert services.is_open(test, now=at(10))
    assert announced() == ["Ali", "Bekzod", "Dilnoza"]
    output = capsys.readouterr().out
    assert "Xabar yuborildi: 3 ta o'quvchiga." in output
    assert "Xabar yuborildi: 0 ta o'quvchiga." in output
    assert "- Python-1: 3 o'quvchi, bankda 24 ta savol — bugun: Ochiq" in output


def test_send_opens_missing_test_and_reaches_late_joiner(world: World) -> None:
    run("send", at(9))
    newcomer = make_user("+998901000014", Role.STUDENT, name="Erkin")
    Enrollment.objects.create(user=newcomer, course=world.course, group=world.group)
    run("send", at(12))

    assert DailyTest.objects.get(group=world.group).status == DailyTest.Status.OPEN
    assert announced() == ["Ali", "Bekzod", "Dilnoza", "Erkin"]


@pytest.mark.parametrize("moment", [at(6, 30), at(23, 0)])
def test_send_only_between_7_and_23(world: World, moment: datetime) -> None:
    with pytest.raises(SystemExit, match="07:00 dan 23:00 gacha"):
        run("send", moment)

    assert not DailyTest.objects.exists()
    assert announced() == []
