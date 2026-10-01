"""Saytdagi chat API: cookie, CSRF, navbat, limitlar va test rejimidagi to'liq suhbat."""

from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assistant.agent import partial_key
from apps.assistant.models import AssistantSettings, Conversation, Message
from apps.assistant.views import COOKIE_NAME
from apps.catalog.models import Course
from apps.leads.models import Lead
from apps.users.models import User

pytestmark = pytest.mark.django_db

URL = "/api/v1/assistant/chat/"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def dry_run(settings: Any) -> None:
    settings.ASSISTANT_DRY_RUN = True


def send(client: APIClient, text: str, **extra: Any) -> Any:
    return client.post(URL, {"text": text, "page": "/uz", **extra}, format="json")


def test_state_without_conversation(client: APIClient) -> None:
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == {"conversation": None, "messages": [], "draft": ""}


def test_disabled_when_not_configured(client: APIClient) -> None:
    response = send(client, "Salom")

    assert response.status_code == 503
    assert not Conversation.objects.exists()


def test_disabled_in_admin(client: APIClient, dry_run: None) -> None:
    AssistantSettings.objects.update_or_create(pk=1, defaults={"enabled": False})

    assert send(client, "Salom").status_code == 503


def test_first_message_creates_conversation_and_cookie(client: APIClient, dry_run: None) -> None:
    with mock.patch("apps.assistant.views.answer.delay"):
        response = send(client, "Salom", HTTP_ACCEPT_LANGUAGE="ru")

    assert response.status_code == 202
    cookie = response.cookies[COOKIE_NAME]
    assert cookie["httponly"] and cookie["path"] == "/api/v1/assistant/"
    conversation = Conversation.objects.get()
    # Bazada kalitning o'zi emas, xeshi.
    assert conversation.token_hash and conversation.token_hash != cookie.value
    assert conversation.source_page == "/uz"
    body = response.json()
    assert body["conversation"]["pending"] is True
    assert [message["text"] for message in body["messages"]] == ["Salom"]


def test_reply_flow_in_dry_run(
    client: APIClient,
    dry_run: None,
    courses: list[Course],
    django_capture_on_commit_callbacks: Any,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        send(client, "Salom, kurslar haqida")

    state = client.get(URL).json()
    assert state["conversation"]["pending"] is False
    _user, reply = state["messages"]
    assert reply["role"] == "assistant"
    assert reply["text"].startswith("🧪 Test rejimi")
    assert {card["slug"] for card in reply["attachments"]} >= {"frontend"}

    # Raqam yozilsa — ariza yaratiladi (AI'siz rejimda ham).
    with (
        django_capture_on_commit_callbacks(execute=True),
        mock.patch("apps.leads.services.notify_new_lead.delay"),
    ):
        send(client, "Aziz, 90 123 45 67")

    state = client.get(URL, {"after": reply["id"]}).json()
    assert [message["role"] for message in state["messages"]] == ["user", "assistant"]
    assert "Arizangiz qabul qilindi" in state["messages"][-1]["text"]
    assert state["conversation"]["has_lead"] is True
    assert Lead.objects.get().source == Lead.Source.AI_WEB


def test_second_message_while_pending_is_rejected(client: APIClient, dry_run: None) -> None:
    with mock.patch("apps.assistant.views.answer.delay"):
        send(client, "Birinchi")
        response = send(client, "Ikkinchi")

    assert response.status_code == 409
    assert response.json()["code"] == "busy"


def test_stale_pending_is_released(client: APIClient, dry_run: None) -> None:
    with mock.patch("apps.assistant.views.answer.delay"):
        send(client, "Birinchi")
        Conversation.objects.update(pending_since=timezone.now() - timedelta(minutes=5))
        response = send(client, "Ikkinchi")

    assert response.status_code == 202


def test_draft_is_returned_while_pending(client: APIClient, dry_run: None) -> None:
    with mock.patch("apps.assistant.views.answer.delay"):
        send(client, "Raqamim 90 123 45 67")
    conversation = Conversation.objects.get()
    cache.set(partial_key(conversation.pk), "Rahmat, ‹telefon-1›", 60)

    assert client.get(URL).json()["draft"] == "Rahmat, +998901234567"


def test_csrf_is_required_for_guests(dry_run: None) -> None:
    client = APIClient(enforce_csrf_checks=True)

    assert send(client, "Salom").status_code == 403


def test_logged_in_user_is_linked_with_account_placeholder(
    client: APIClient, dry_run: None
) -> None:
    user = User.objects.create_user(phone="+998935556677", password="x", first_name="Dilnoza")
    client.force_authenticate(user)

    with mock.patch("apps.assistant.views.answer.delay"):
        send(client, "Salom")

    conversation = Conversation.objects.get()
    assert conversation.user == user and conversation.name == "Dilnoza"
    context = Message.objects.get(role=Message.Role.USER).content[0]["text"]
    assert "raqami ‹telefon-akkaunt›" in context and "+998" not in context


def test_closed_conversation_starts_new(client: APIClient, dry_run: None) -> None:
    with mock.patch("apps.assistant.views.answer.delay"):
        send(client, "Birinchi")
        Conversation.objects.update(status=Conversation.Status.CLOSED, pending_since=None)
        send(client, "Yangi savol")

    assert Conversation.objects.count() == 2


def test_forget_clears_cookie(client: APIClient, dry_run: None) -> None:
    with mock.patch("apps.assistant.views.answer.delay"):
        send(client, "Salom")

    response = client.delete(URL)

    assert response.status_code == 204
    assert response.cookies[COOKIE_NAME].value == ""
    assert client.get(URL).json()["conversation"] is None


def test_rate_answer(client: APIClient, dry_run: None, conversation: Conversation) -> None:
    with mock.patch("apps.assistant.views.answer.delay"):
        send(client, "Salom")
    mine = Conversation.objects.exclude(pk=conversation.pk).get()
    answer = Message.objects.create(conversation=mine, role=Message.Role.ASSISTANT, text="Javob")
    foreign = Message.objects.create(
        conversation=conversation, role=Message.Role.ASSISTANT, text="Boshqa suhbat"
    )

    ok = client.post(f"{URL}rate/", {"message": answer.pk, "rating": -1}, format="json")
    other = client.post(f"{URL}rate/", {"message": foreign.pk, "rating": 1}, format="json")

    assert ok.status_code == 204 and other.status_code == 404
    answer.refresh_from_db()
    assert answer.rating == Message.Rating.BAD


def test_long_message_is_rejected(client: APIClient, dry_run: None) -> None:
    assert send(client, "a" * 1001).status_code == 400


def test_site_flag(client: APIClient, settings: Any) -> None:
    assert client.get("/api/v1/site/").json()["settings"]["assistant_enabled"] is False

    settings.ASSISTANT_DRY_RUN = True
    AssistantSettings.load().save()  # sozlama saqlanganda sayt keshi tozalanadi

    assert client.get("/api/v1/site/").json()["settings"]["assistant_enabled"] is True
