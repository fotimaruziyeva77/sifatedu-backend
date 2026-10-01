"""Admin: xabar yozish, tasdiqlash oynasi, yuborish va ruxsatlar."""

from typing import Any
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse

from apps.notifications.models import Broadcast, Notification
from apps.users.models import User
from apps.users.roles import Role, set_roles

from .conftest import make_student

pytestmark = pytest.mark.django_db

SUBMIT = {"_form_submitted": "True"}


def login_as(phone: str, role: str) -> tuple[Client, User]:
    user = User.objects.create_user(phone=phone, password="x", first_name="Xodim")
    set_roles(user, [role])
    client = Client()
    client.force_login(user)
    return client, user


def draft(**fields: Any) -> Broadcast:
    return Broadcast.objects.create(title="Ertaga dars yo'q", body="Dam oling", **fields)


def test_manager_writes_and_sends(
    sent: mock.MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    make_student("+998901000001", telegram_id=1)
    make_student("+998901000002")
    client, manager = login_as("+998909000001", Role.MANAGER)

    created = client.post(
        reverse("admin:notifications_broadcast_add"),
        {
            "title": "Ertaga dars yo'q",
            "body": "Dam oling",
            "link": "",
            "kind": Broadcast.Kind.INFO,
            "audience": Broadcast.Audience.ALL,
            "send_telegram": "on",
            "sms_text": "",
        },
    )
    message = Broadcast.objects.get()
    summary = client.get(
        reverse("admin:notifications_broadcast_send_now", args=[message.pk]), HTTP_HX_REQUEST="true"
    )
    with django_capture_on_commit_callbacks(execute=True):
        confirmed = client.post(
            reverse("admin:notifications_broadcast_send_now", args=[message.pk]),
            SUBMIT,
            HTTP_HX_REQUEST="true",
        )

    assert created.status_code == 302 and message.created_by == manager
    # Tasdiqlash oynasida raqamlar: 2 kishi, 1 tasi Telegram orqali.
    assert summary.status_code == 200
    assert "Jami qabul qiluvchilar" in summary.content.decode()
    assert confirmed["HX-Redirect"].endswith(f"/{message.pk}/change/")
    message.refresh_from_db()
    assert message.status == Broadcast.Status.SENT and message.recipients == 2
    assert sent.call_count == 1


def test_sent_message_is_locked(django_capture_on_commit_callbacks: Any) -> None:
    make_student("+998901000003")
    client, _manager = login_as("+998909000002", Role.MANAGER)
    message = draft()
    url = reverse("admin:notifications_broadcast_send_now", args=[message.pk])
    with django_capture_on_commit_callbacks(execute=True):
        client.post(url, SUBMIT)

    page = client.get(reverse("admin:notifications_broadcast_change", args=[message.pk]))
    again = client.post(url, SUBMIT)

    assert "title" not in page.context["adminform"].form.fields
    assert again.status_code == 403
    assert Notification.objects.count() == 1
    assert not page.context["has_delete_permission"]


def test_empty_audience_is_not_sent() -> None:
    client, _manager = login_as("+998909000003", Role.MANAGER)
    message = draft(without_course=True)

    client.post(reverse("admin:notifications_broadcast_send_now", args=[message.pk]), SUBMIT)

    message.refresh_from_db()
    assert message.status == Broadcast.Status.DRAFT


def test_test_send_goes_only_to_author(django_capture_on_commit_callbacks: Any) -> None:
    make_student("+998901000004")
    client, manager = login_as("+998909000004", Role.MANAGER)
    message = draft()

    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("admin:notifications_broadcast_send_test", args=[message.pk]), SUBMIT)

    [notification] = Notification.objects.all()
    assert notification.user == manager and notification.title.startswith("[Sinov]")
    message.refresh_from_db()
    assert message.status == Broadcast.Status.DRAFT


@pytest.mark.parametrize(
    ("role", "list_status", "send_status"),
    [(Role.DIRECTOR, 200, 403), (Role.TEACHER, 403, 403), (Role.ADMIN, 200, 302)],
)
def test_who_can_send(role: str, list_status: int, send_status: int) -> None:
    make_student("+998901000005")
    client, _user = login_as("+998909000005", role)
    message = draft()

    listing = client.get(reverse("admin:notifications_broadcast_changelist"))
    sending = client.post(
        reverse("admin:notifications_broadcast_send_now", args=[message.pk]), SUBMIT
    )

    assert listing.status_code == list_status
    assert sending.status_code == send_status


def test_delivery_log_is_read_only() -> None:
    student = make_student("+998901000006")
    Notification.objects.create(user=student, kind=Notification.Kind.TEST, title="A")
    client, _manager = login_as("+998909000006", Role.MANAGER)

    listing = client.get(
        reverse("admin:notifications_notification_changelist"), {"delivery": "site"}
    )

    assert listing.status_code == 200
    assert len(listing.context["cl"].result_list) == 1
    assert not listing.context["has_add_permission"]
