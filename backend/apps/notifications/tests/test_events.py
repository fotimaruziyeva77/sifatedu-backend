"""Avtomatik xabarlar: to'lov, qo'lda ochilgan kurs, offlayn to'lov muddati eslatmalari."""

from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category, Course
from apps.learning.models import Enrollment
from apps.notifications import services
from apps.notifications.models import Delivery, Notification
from apps.notifications.tasks import remind_expiring
from apps.payments.models import Order, PaymentTransaction
from apps.payments.tasks import finish_payment
from apps.users.models import User
from apps.users.roles import Role, set_roles

from .conftest import make_student

pytestmark = pytest.mark.django_db


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="it", name_uz="IT")
    return Course.objects.create(
        slug="frontend", title_uz="Frontend", title_ru="Фронтенд", category=category
    )


def paid(user: User, course: Course) -> PaymentTransaction:
    order = Order.objects.create(user=user, course=course, amount=500_000, status=Order.Status.PAID)
    return PaymentTransaction.objects.create(
        order=order,
        provider_trans_id=f"t-{user.pk}",
        amount=500_000,
        status=PaymentTransaction.Status.CONFIRMED,
    )


def test_payment_goes_to_telegram_or_sms(
    course: Course, sent: mock.MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    with_telegram = make_student("+998901000001", telegram_id=1, locale="ru")
    without = make_student("+998901000002")

    with (
        mock.patch.object(services, "send_sms") as sms,
        django_capture_on_commit_callbacks(execute=True),
    ):
        finish_payment(paid(with_telegram, course).pk)
        finish_payment(paid(without, course).pk)

    telegram_note = Notification.objects.get(user=with_telegram)
    sms_note = Notification.objects.get(user=without)
    assert telegram_note.kind == Notification.Kind.PAYMENT
    assert telegram_note.title == "Оплата получена" and "«Фронтенд»" in telegram_note.body
    assert telegram_note.link == "/dashboard/courses/frontend"
    assert (telegram_note.telegram, telegram_note.sms) == (Delivery.SENT, "")
    # Telegram'i yo'q o'quvchi oldingidek SMS oladi.
    assert (sms_note.telegram, sms_note.sms) == ("", Delivery.SENT)
    sms.assert_called_once()
    assert "«Frontend» kursi ochildi" in sms.call_args.args[1]


def test_manual_enrollment_notifies_student(
    course: Course, django_capture_on_commit_callbacks: Any
) -> None:
    student = make_student()
    manager = User.objects.create_user(phone="+998909000001", password="x")
    set_roles(manager, [Role.MANAGER])
    client = Client()
    client.force_login(manager)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("admin:learning_enrollment_add"),
            {
                "user": student.pk,
                "course": course.pk,
                "status": Enrollment.Status.ACTIVE,
                "source": Enrollment.Source.MANUAL,
                "study_format": Enrollment.Format.ONLINE,
            },
        )

    assert response.status_code == 302
    note = Notification.objects.get(user=student)
    assert note.kind == Notification.Kind.COURSE_OPENED
    assert "«Frontend»" in note.body


def test_offline_expiry_reminders_are_sent_once(
    course: Course, django_capture_on_commit_callbacks: Any
) -> None:
    now = timezone.now()
    soon = make_student("+998901000011")
    gone = make_student("+998901000012")
    later = make_student("+998901000013")
    online = make_student("+998901000014")
    offline = Enrollment.Format.OFFLINE
    Enrollment.objects.create(
        user=soon, course=course, study_format=offline, expires_at=now + timedelta(days=2)
    )
    Enrollment.objects.create(
        user=gone, course=course, study_format=offline, expires_at=now - timedelta(hours=5)
    )
    Enrollment.objects.create(
        user=later, course=course, study_format=offline, expires_at=now + timedelta(days=20)
    )
    Enrollment.objects.create(user=online, course=course)

    with django_capture_on_commit_callbacks(execute=True):
        first = remind_expiring()
        second = remind_expiring()

    kinds = dict(Notification.objects.values_list("user__phone", "kind"))
    assert (first, second) == ("2", "0")
    assert kinds == {
        "+998901000011": Notification.Kind.ACCESS_EXPIRING,
        "+998901000012": Notification.Kind.ACCESS_EXPIRED,
    }
    reminder = Notification.objects.get(user=soon)
    assert reminder.link == "/dashboard/catalog/frontend"
    assert "kuni tugaydi" in reminder.body
