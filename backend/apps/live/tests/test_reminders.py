"""Eslatmalar: kun ichida va 30 daqiqa oldin, har biri bir marta; kimlarga boradi."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.learning.models import Enrollment
from apps.live import services
from apps.live.models import LiveLesson
from apps.notifications.models import Notification

from .conftest import MONDAY, World, live, local

pytestmark = pytest.mark.django_db
EVENING = local(MONDAY, "18:00")


def reminders() -> list[Notification]:
    return list(Notification.objects.filter(kind=Notification.Kind.LIVE_REMINDER).order_by("pk"))


def test_day_and_soon_reminders_go_once_to_students_and_teacher(world: World) -> None:
    live(world, EVENING)

    services.remind(now=EVENING - timedelta(hours=20))
    services.remind(now=EVENING - timedelta(hours=19, minutes=55))
    day = reminders()
    services.remind(now=EVENING - timedelta(minutes=30))
    services.remind(now=EVENING - timedelta(minutes=25))
    soon = reminders()[len(day) :]

    assert {note.user for note in day} == {world.student, world.classmate, world.teacher}
    assert {note.user for note in soon} == {world.student, world.classmate, world.teacher}
    first = next(note for note in day if note.user == world.student)
    assert first.title == "Jonli dars: 5-oktabr, 18:00"
    assert first.body == "«FE-1» guruhi, Frontend. Onlayn — «Qo'shilish» tugmasi jadvalda."
    assert next(note for note in soon if note.user == world.student).title == (
        "Dars soat 18:00 da boshlanadi"
    )


def test_quiet_window_canceled_and_unpaid_get_nothing(world: World) -> None:
    lesson = live(world, EVENING, kind="OFFLINE", meet_url="", room="3-xona")
    expired = world.classmate.enrollments.get()
    Enrollment.objects.filter(pk=expired.pk).update(expires_at=EVENING - timedelta(days=2))

    # 35 daqiqadan 2 soatgacha — eslatma yo'q (kunlik yuborilgan, 30 daqiqalik hali erta).
    services.remind(now=EVENING - timedelta(hours=1))
    assert reminders() == []
    services.remind(now=EVENING - timedelta(hours=5))
    assert {note.user for note in reminders()} == {world.student, world.teacher}
    assert reminders()[0].body == "«FE-1» guruhi, Frontend. Offlayn, 3-xona."
    LiveLesson.objects.filter(pk=lesson.pk).update(canceled_at=timezone.now())
    services.remind(now=EVENING - timedelta(minutes=30))
    assert len(reminders()) == 2


def test_reminder_is_in_the_students_language(world: World) -> None:
    world.student.locale = "ru"
    world.student.save(update_fields=["locale"])
    live(world, EVENING)

    services.remind(now=EVENING - timedelta(minutes=20))

    note = Notification.objects.get(user=world.student)
    assert note.title == "Урок начнётся в 18:00"
