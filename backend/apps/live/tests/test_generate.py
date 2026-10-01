"""Haftalik jadvaldan darslar: 14 kun oldinga, takrorlanmaydi, jadval o'zgarsa moslanadi."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.learning.models import StudyGroup
from apps.live import services
from apps.live.models import Attendance, LiveLesson, ScheduleSlot

from .conftest import MEET, MONDAY, World, local

pytestmark = pytest.mark.django_db
NOON = local(MONDAY, "12:00")


def times(world: World) -> list[str]:
    return [
        f"{timezone.localtime(lesson.starts_at):%d.%m %H:%M}"
        for lesson in world.group.live_lessons.order_by("starts_at")
    ]


def test_two_weeks_are_generated_from_the_weekly_slots(world: World) -> None:
    created = services.generate(world.group, now=NOON)

    assert created == 4
    assert times(world) == ["05.10 18:00", "07.10 18:00", "12.10 18:00", "14.10 18:00"]
    first = world.group.live_lessons.order_by("starts_at").first()
    assert first is not None
    # Toshkent vaqti UTC+5.
    assert first.starts_at == datetime(2026, 10, 5, 13, 0, tzinfo=UTC)
    assert (first.kind, first.meet_url, first.duration_min, first.generated) == (
        "ONLINE",
        MEET,
        90,
        True,
    )
    assert (
        world.group.live_lessons.get(starts_at=local(MONDAY + timedelta(2), "18:00")).duration_min
        == 120
    )
    # Qayta ishga tushsa ham, bekor qilingani ham qayta yaratilmaydi.
    LiveLesson.objects.filter(pk=first.pk).update(canceled_at=NOON)
    assert services.generate(world.group, now=NOON) == 0
    assert world.group.live_lessons.count() == 4


def test_lessons_before_start_date_or_in_finished_groups_are_skipped(world: World) -> None:
    StudyGroup.objects.filter(pk=world.group.pk).update(starts_on=date(2026, 10, 10))
    world.group.refresh_from_db()

    assert services.generate(world.group, now=NOON) == 2
    StudyGroup.objects.filter(pk=world.group.pk).update(status=StudyGroup.Status.FINISHED)
    world.group.refresh_from_db()
    assert services.planned_times(world.group, now=NOON) == {}


def test_past_slots_of_today_are_not_created(world: World) -> None:
    evening = local(MONDAY, "19:00")

    services.generate(world.group, now=evening)

    assert times(world)[0] == "07.10 18:00"


def test_sync_follows_schedule_changes_without_touching_used_lessons(world: World) -> None:
    services.generate(world.group, now=NOON)
    lessons = {
        f"{timezone.localtime(item.starts_at):%d.%m}": item
        for item in world.group.live_lessons.all()
    }
    # 7-oktabrdagi darsga o'quvchi qo'shilgan, 12-oktabrdagi qo'lda o'zgartirilgan.
    Attendance.objects.create(live_lesson=lessons["07.10"], student=world.student, joined_at=NOON)
    LiveLesson.objects.filter(pk=lessons["12.10"].pk).update(generated=False, title="Maxsus")
    ScheduleSlot.objects.filter(group=world.group, weekday=2).update(starts_at=time(19, 0))
    world.group.meet_url = "https://meet.google.com/new-link-xyz"
    world.group.save()

    created, removed = services.sync(world.group, now=NOON)

    # Chorshanba 19:00 ga ko'chdi: 14-oktabrdagi eski dars o'chdi, yangilari yaratildi. Qo'shilgan
    # (7-oktabr, 18:00) va qo'lda o'zgartirilgan (12-oktabr) darslar joyida qoldi.
    assert (created, removed) == (2, 1)
    assert times(world) == [
        "05.10 18:00",
        "07.10 18:00",
        "07.10 19:00",
        "12.10 18:00",
        "14.10 19:00",
    ]
    kept = world.group.live_lessons.get(pk=lessons["05.10"].pk)
    assert kept.meet_url == "https://meet.google.com/new-link-xyz"
    assert world.group.live_lessons.get(pk=lessons["07.10"].pk).meet_url == MEET
    assert world.group.live_lessons.get(pk=lessons["12.10"].pk).title == "Maxsus"
    assert not world.group.live_lessons.filter(pk=lessons["14.10"].pk).exists()


def test_offline_group_gets_the_room(world: World) -> None:
    StudyGroup.objects.filter(pk=world.group.pk).update(study_format="OFFLINE", room="3-xona")
    world.group.refresh_from_db()

    services.generate(world.group, now=NOON)

    lesson = world.group.live_lessons.first()
    assert lesson is not None
    assert (lesson.kind, lesson.meet_url, lesson.room) == ("OFFLINE", "", "3-xona")
