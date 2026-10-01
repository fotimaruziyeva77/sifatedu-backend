"""Ommaviy xabar: auditoriya filtrlari, qamrov, tungi vaqt, bir marta yuborish."""

from datetime import date, datetime, timedelta
from typing import Any
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.catalog.models import Category, Course
from apps.learning.models import Enrollment, StudyGroup
from apps.notifications import services
from apps.notifications.models import Broadcast, Delivery, Notification
from apps.notifications.tasks import send_scheduled_broadcasts
from apps.users.models import SocialAccount, User

from .conftest import make_student

pytestmark = pytest.mark.django_db

TASHKENT = ZoneInfo("Asia/Tashkent")


@pytest.fixture
def courses(db: Any) -> tuple[Course, Course]:
    category = Category.objects.create(slug="it", name_uz="IT")
    return (
        Course.objects.create(slug="frontend", title_uz="Frontend", category=category),
        Course.objects.create(slug="backend", title_uz="Backend", category=category),
    )


def broadcast(**fields: Any) -> Broadcast:
    fields.setdefault("title", "Ertaga dars yo'q")
    fields.setdefault("body", "Dam oling!")
    return Broadcast.objects.create(**fields)


def phones(users: Any) -> set[str]:
    return {user.phone for user in users}


def test_audience_filters(courses: tuple[Course, Course]) -> None:
    frontend, backend = courses
    adult = make_student("+998901000001")
    kid = make_student("+998901000002", audience=User.Audience.KIDS)
    idle = make_student("+998901000003")
    make_student("+998901000004", is_active=False)
    make_student("+998901000005", is_staff=True)
    Enrollment.objects.create(user=adult, course=frontend)
    Enrollment.objects.create(user=kid, course=backend)
    Enrollment.objects.create(user=idle, course=backend, status=Enrollment.Status.CANCELLED)

    everyone = broadcast()
    kids = broadcast(audience=Broadcast.Audience.KIDS)
    on_frontend = broadcast()
    on_frontend.courses.add(frontend)
    no_course = broadcast(without_course=True)

    assert phones(services.recipients(everyone)) == {
        "+998901000001",
        "+998901000002",
        "+998901000003",
    }
    assert phones(services.recipients(kids)) == {"+998901000002"}
    assert phones(services.recipients(on_frontend)) == {"+998901000001"}
    # Bekor qilingan yozilish "kurs yo'q" hisoblanadi.
    assert phones(services.recipients(no_course)) == {"+998901000003"}


def test_group_and_join_date_filters(courses: tuple[Course, Course]) -> None:
    frontend, _backend = courses
    teacher = make_student("+998901000010", is_staff=True)
    group = StudyGroup.objects.create(course=frontend, teacher=teacher, name="FE-1")
    member = make_student("+998901000011")
    other = make_student("+998901000012")
    Enrollment.objects.create(user=member, course=frontend, group=group)
    Enrollment.objects.create(user=other, course=frontend)
    User.objects.filter(pk=member.pk).update(
        date_joined=datetime(2026, 9, 1, 23, 30, tzinfo=TASHKENT)
    )

    in_group = broadcast()
    in_group.groups.add(group)
    september_first = broadcast(joined_from=date(2026, 9, 1), joined_to=date(2026, 9, 1))

    assert phones(services.recipients(in_group)) == {"+998901000011"}
    assert phones(services.recipients(september_first)) == {"+998901000011"}


def test_reach_counts_channels_and_sms_cost(settings: Any) -> None:
    settings.SMS_PRICE_UZS = 90
    make_student("+998901000021", telegram_id=21)
    make_student("+998901000022", telegram_id=22, consent=True)
    make_student("+998901000023")
    make_student("+998901000024", consent=True)
    blocked = make_student("+998901000025", telegram_id=25)
    SocialAccount.objects.filter(user=blocked).update(blocked_at=timezone.now())

    info = broadcast(send_sms=True, sms_text="Ertaga dars yo'q")
    promo = broadcast(kind=Broadcast.Kind.PROMO, send_sms=True, sms_text="Chegirma 20%")

    assert services.reach(info) == services.Reach(total=5, telegram=2, sms=3, sms_cost=270)
    # Aksiya: Telegram va SMS faqat rozilik berganlarga, qolganlar kabinetda ko'radi.
    promo_reach = services.reach(promo)
    assert (promo_reach.telegram, promo_reach.sms, promo_reach.site_only) == (1, 1, 3)


def test_send_creates_inbox_items_once(
    sent: mock.MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    linked = make_student("+998901000031", telegram_id=31)
    make_student("+998901000032")
    message = broadcast(link="https://meet.google.com/abc-defg-hij")
    staff = make_student("+998901000039", is_staff=True)

    with django_capture_on_commit_callbacks(execute=True):
        later = services.schedule(message, staff)
    services.send(message.pk)  # ikkinchi marta — hech narsa qilmaydi

    message.refresh_from_db()
    assert later is None
    assert message.status == Broadcast.Status.SENT and message.recipients == 2
    assert message.created_by == staff
    assert Notification.objects.filter(broadcast=message).count() == 2
    assert Notification.objects.get(user=linked).telegram == Delivery.SENT
    assert sent.call_count == 1


def test_promo_waits_for_morning(django_capture_on_commit_callbacks: Any) -> None:
    make_student("+998901000041", consent=True)
    staff = make_student("+998901000049", is_staff=True)
    promo = broadcast(kind=Broadcast.Kind.PROMO)
    night = datetime(2026, 9, 29, 23, 15, tzinfo=TASHKENT)

    with (
        mock.patch.object(services.timezone, "now", return_value=night),
        django_capture_on_commit_callbacks(execute=True),
    ):
        later = services.schedule(promo, staff)

    promo.refresh_from_db()
    assert later == datetime(2026, 9, 30, 9, 0, tzinfo=TASHKENT)
    assert promo.status == Broadcast.Status.SCHEDULED
    assert not Notification.objects.exists()

    # Ertalab beat navbatdagilarini yuboradi.
    Broadcast.objects.filter(pk=promo.pk).update(
        scheduled_for=timezone.now() - timedelta(minutes=1)
    )
    with django_capture_on_commit_callbacks(execute=True):
        send_scheduled_broadcasts()
    promo.refresh_from_db()
    assert promo.status == Broadcast.Status.SENT and promo.recipients == 1


def test_quiet_hours_boundaries() -> None:
    assert services.in_quiet_hours(datetime(2026, 9, 29, 22, 0, tzinfo=TASHKENT))
    assert services.in_quiet_hours(datetime(2026, 9, 29, 8, 59, tzinfo=TASHKENT))
    assert not services.in_quiet_hours(datetime(2026, 9, 29, 9, 0, tzinfo=TASHKENT))
    morning = services.next_morning(datetime(2026, 9, 29, 3, 0, tzinfo=TASHKENT))
    assert morning == datetime(2026, 9, 29, 9, 0, tzinfo=TASHKENT)
