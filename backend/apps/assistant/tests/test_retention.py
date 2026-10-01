"""TZ 4.9: 90 kundan eski suhbatlar anonimlashtiriladi, statistika qoladi."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.assistant.models import Conversation, Message
from apps.assistant.tasks import anonymize_old_conversations

pytestmark = pytest.mark.django_db


def test_old_conversations_are_anonymized() -> None:
    old = Conversation.objects.create(
        name="Aziz",
        phones={"1": "+998901234567"},
        telegram_chat_id=555,
        token_hash="x" * 64,
        user_messages=4,
        cost_usd=Decimal("0.05"),
        last_message_at=timezone.now() - timedelta(days=91),
    )
    Message.objects.create(conversation=old, role=Message.Role.USER, text="90 123 45 67")
    fresh = Conversation.objects.create(name="Vali", last_message_at=timezone.now())

    assert anonymize_old_conversations() == 1

    old.refresh_from_db()
    assert (old.name, old.phones, old.telegram_chat_id, old.token_hash) == ("", {}, None, None)
    assert old.anonymized_at is not None
    assert (old.user_messages, old.cost_usd) == (4, Decimal("0.05"))
    assert old.messages.get().text == ""
    fresh.refresh_from_db()
    assert fresh.name == "Vali"
