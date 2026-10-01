"""AI maslahatchi Telegram botda: erkin matnga javob va javob formati.

/start, ro'yxatdan o'tish, menyu va webhook — apps/bot/tests.
"""

from typing import Any
from unittest import mock

import pytest

from apps.assistant import telegram
from apps.assistant.models import Conversation
from apps.assistant.telegram import answer, render
from apps.catalog.models import Course

pytestmark = pytest.mark.django_db

SENDER = {"first_name": "Aziz", "last_name": "", "username": "aziz"}


@pytest.fixture
def sent() -> Any:
    with (
        mock.patch.object(telegram.telegram_api, "send_message") as send,
        mock.patch.object(telegram.telegram_api, "call"),
    ):
        yield send


@pytest.fixture
def dry_run(settings: Any) -> None:
    settings.ASSISTANT_DRY_RUN = True


def test_text_gets_answer(sent: Any, dry_run: None, courses: list[Course]) -> None:
    answer(555, SENDER, "Qanday kurslar bor?", "uz")

    text = sent.call_args.args[1]
    assert text.startswith("🧪 Test rejimi")
    assert "http://localhost/uz/courses/frontend" in text
    # Botning pastki menyusi o'z joyida qoladi.
    assert sent.call_args.kwargs.get("reply_markup") is None
    conversation = Conversation.objects.get()
    assert conversation.channel == Conversation.Channel.TELEGRAM
    assert (conversation.telegram_chat_id, conversation.telegram_username) == (555, "aziz")
    assert conversation.locale == "uz" and conversation.pending_since is None


def test_same_chat_continues_conversation(sent: Any, dry_run: None) -> None:
    answer(555, SENDER, "Salom", "ru")
    answer(555, SENDER, "Narxlar qancha?", "ru")

    conversation = Conversation.objects.get()
    assert conversation.locale == "ru" and conversation.user_messages == 2


def test_rate_limit(sent: Any, dry_run: None) -> None:
    with mock.patch.object(telegram, "MAX_PER_HOUR", 1), mock.patch.object(telegram, "respond"):
        answer(555, SENDER, "Birinchi", "uz")
        answer(555, SENDER, "Ikkinchi", "uz")
    assert "juda ko'p" in sent.call_args.args[1]


def test_render_escapes_html_and_keeps_bold() -> None:
    card = {"slug": "frontend", "title": "Frontend <b>", "price_online": 1_200_000}

    html = render("**Frontend** — <script>", [card], "ru")

    assert html.startswith("<b>Frontend</b> — &lt;script&gt;")
    assert (
        "<b>Frontend &lt;b&gt;</b> — 1 200 000 so'm\nhttp://localhost/ru/courses/frontend" in html
    )
