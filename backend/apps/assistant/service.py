"""Sayt va Telegram uchun umumiy: mijoz xabarini saqlash va javob navbatini egallash."""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Conversation, Message
from .phones import ACCOUNT_KEY, hide_cards, mask_phones
from .prompt import context_block

MAX_TEXT_LENGTH = 1000
# Javob shundan uzoq tayyorlanayotgan bo'lsa, worker to'xtab qolgan deb hisoblanadi.
PENDING_TIMEOUT = timedelta(seconds=90)


def is_pending(conversation: Conversation) -> bool:
    since = conversation.pending_since
    return since is not None and timezone.now() - since < PENDING_TIMEOUT


def claim(conversation: Conversation) -> bool:
    """Javob navbatini atomik egallaydi. Oldingi javob hali tayyorlanayotgan bo'lsa — False."""
    now = timezone.now()
    free = Q(pending_since__isnull=True) | Q(pending_since__lt=now - PENDING_TIMEOUT)
    taken = Conversation.objects.filter(free, pk=conversation.pk).update(pending_since=now)
    if taken:
        conversation.pending_since = now
    return bool(taken)


def release(conversation: Conversation) -> None:
    Conversation.objects.filter(pk=conversation.pk).update(pending_since=None)
    conversation.pending_since = None


def attach_user_phone(conversation: Conversation, phone: str) -> None:
    """Saytga kirgan mijozning akkaunt raqami: AI uni faqat ‹telefon-akkaunt› deb ko'radi."""
    if phone and conversation.phones.get(ACCOUNT_KEY) != phone:
        conversation.phones = {**conversation.phones, ACCOUNT_KEY: phone}


def add_user_message(
    conversation: Conversation,
    text: str,
    *,
    page: str = "",
    quiz: dict[str, str] | None = None,
    announce_user: bool = False,
) -> Message:
    """Mijoz xabarini saqlaydi. Modelga boradigan nusxada raqamlar belgi bilan almashtiriladi."""
    shown = hide_cards(text.strip())[:MAX_TEXT_LENGTH]
    phones = dict(conversation.phones)
    masked = mask_phones(shown, phones)
    # Mijoz o'zi "<kontekst>" yozib, xizmat ma'lumotiga o'xshatolmasin.
    masked = masked.replace("<kontekst", "‹kontekst").replace("</kontekst", "‹/kontekst")
    conversation.phones = phones
    context = context_block(conversation, page=page, quiz=quiz, announce_user=announce_user)

    now = timezone.now()
    conversation.user_messages += 1
    conversation.last_message_at = now
    conversation.save(update_fields=["phones", "user_messages", "last_message_at", "updated_at"])
    return Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        text=shown,
        content=[{"type": "text", "text": context}, {"type": "text", "text": masked}],
    )
