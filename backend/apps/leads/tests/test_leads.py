from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.catalog.models import Category, Course
from apps.leads.models import Lead
from apps.leads.tasks import notify_new_lead
from apps.notifications import telegram

URL = "/api/v1/leads/"


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    # Throttle hisoblagichlari keshda saqlanadi.
    cache.clear()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="frontend", name_uz="Frontend")
    return Course.objects.create(
        slug="frontend-dasturlash",
        title_uz="Frontend",
        category=category,
        status=Course.Status.PUBLISHED,
    )


def payload(**overrides: Any) -> dict[str, Any]:
    return {"name": "Ali", "phone": "+998 90 123-45-67", **overrides}


@pytest.mark.django_db
def test_lead_is_created_with_normalized_phone(
    client: APIClient, course: Course, django_capture_on_commit_callbacks: Any
) -> None:
    with (
        mock.patch("apps.leads.services.notify_new_lead.delay") as notify,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = client.post(
            URL,
            payload(course=course.slug, utm_source="instagram", source_page="/uz"),
            HTTP_ACCEPT_LANGUAGE="ru",
            HTTP_X_FORWARDED_FOR="203.0.113.7",
        )

    assert response.status_code == 201
    assert response.json() == {"status": "ok"}
    lead = Lead.objects.get()
    assert lead.phone == "+998901234567"
    assert lead.course == course
    assert lead.utm_source == "instagram"
    assert lead.locale == "ru"
    assert lead.ip == "203.0.113.7"
    notify.assert_called_once_with(lead.pk)


@pytest.mark.django_db
@pytest.mark.parametrize("phone", ["12345", "+7 912 345 67 89", "abc"])
def test_invalid_phone_is_rejected(client: APIClient, phone: str) -> None:
    response = client.post(URL, payload(phone=phone))

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert "phone" in error["fields"]
    assert not Lead.objects.exists()


@pytest.mark.django_db
def test_unknown_course_is_rejected(client: APIClient) -> None:
    response = client.post(URL, payload(course="yoq-kurs"))

    assert response.status_code == 400
    assert "course" in response.json()["error"]["fields"]


@pytest.mark.django_db
def test_honeypot_returns_ok_but_saves_nothing(client: APIClient) -> None:
    response = client.post(URL, payload(website="http://spam.example"))

    assert response.status_code == 201
    assert not Lead.objects.exists()


@pytest.mark.django_db
def test_duplicate_within_24h_is_merged(client: APIClient) -> None:
    with mock.patch("apps.leads.services.notify_new_lead.delay"):
        client.post(URL, payload(comment="Birinchi"))
        client.post(URL, payload(name="Ali Valiyev", phone="901234567", comment="Ikkinchi"))

    lead = Lead.objects.get()
    assert lead.submissions == 2
    assert lead.name == "Ali Valiyev"
    assert lead.comment == "Birinchi\n---\nIkkinchi"


@pytest.mark.django_db
def test_processed_or_old_lead_is_not_merged(client: APIClient) -> None:
    with mock.patch("apps.leads.services.notify_new_lead.delay"):
        client.post(URL, payload())
        Lead.objects.update(status=Lead.Status.CONTACTED)
        client.post(URL, payload())
        Lead.objects.filter(status=Lead.Status.NEW).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        client.post(URL, payload())

    assert Lead.objects.count() == 3


@pytest.mark.django_db
def test_rate_limit(client: APIClient) -> None:
    with (
        mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"leads": "2/hour"}),
        mock.patch("apps.leads.services.notify_new_lead.delay"),
    ):
        statuses = [client.post(URL, payload()).status_code for _ in range(3)]

    assert statuses == [201, 201, 429]


@pytest.mark.django_db
def test_notify_sends_telegram_message(course: Course) -> None:
    lead = Lead.objects.create(name="<Ali>", phone="+998901234567", course=course)

    with mock.patch.object(telegram, "send_message") as send:
        notify_new_lead(lead.pk)

    text = send.call_args.args[1]
    assert "&lt;Ali&gt;" in text
    assert "+998901234567" in text
    lead.refresh_from_db()
    assert lead.telegram_sent_at is not None


@pytest.mark.django_db
def test_notify_without_telegram_config_is_silent(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = ""
    lead = Lead.objects.create(name="Ali", phone="+998901234567")

    notify_new_lead(lead.pk)

    lead.refresh_from_db()
    assert lead.telegram_sent_at is None
