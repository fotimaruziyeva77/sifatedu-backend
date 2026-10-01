import logging
from datetime import timedelta
from html import escape
from typing import Any

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.notifications import telegram as telegram_api

from .agent import respond
from .models import Conversation
from .service import release
from .tools import admin_link

logger = logging.getLogger(__name__)


# Javob yo'qolsa ham qayta bajarilmaydi (acks_late=False): ikki marta javob yozgandan ko'ra,
# mijoz qayta so'ragani yaxshi. Sayt 90 soniyadan keyin "javob kelmadi" deb ko'rsatadi.
@shared_task(acks_late=False, soft_time_limit=100, time_limit=120)
def answer(conversation_id: int) -> None:
    """Saytdagi xabarga javob (`ai` navbati, `worker-ai`)."""
    conversation = Conversation.objects.filter(pk=conversation_id).first()
    if conversation is None:
        return
    try:
        respond(conversation)
    finally:
        release(conversation)


@shared_task(acks_late=False, soft_time_limit=100, time_limit=120)
def telegram_answer(chat_id: int, sender: dict[str, Any], text: str, locale: str) -> None:
    """Botga yozilgan savolga AI javobi (`ai` navbati)."""
    from . import telegram

    telegram.answer(chat_id, sender, text, locale)


@shared_task(
    autoretry_for=(OSError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def notify_managers(conversation_id: int) -> None:
    """Menejerlar guruhiga: AI suhbatdan takroriy yoki "menejer kerak" murojaat."""
    conversation = Conversation.objects.select_related("lead").filter(pk=conversation_id).first()
    if conversation is None or conversation.lead is None:
        return
    lead = conversation.lead
    lines = [
        "<b>AI suhbat: yangi murojaat</b>",
        f"Holat: {escape(conversation.get_status_display())}",
        f"Ism: {escape(lead.name)}",
        f"Telefon: {escape(lead.phone)}",
    ]
    if conversation.summary:
        lines.append(f"Xulosa: {escape(conversation.summary)}")
    lines.append(f'<a href="{escape(admin_link(conversation))}">Suhbatni ochish</a>')
    try:
        telegram_api.send_message(settings.TELEGRAM_LEADS_CHAT_ID, "\n".join(lines))
    except telegram_api.TelegramNotConfiguredError:
        logger.info("Telegram sozlanmagan: suhbat #%s faqat admin panelda", conversation_id)


@shared_task
def anonymize_old_conversations() -> int:
    """TZ 4.9: suhbatlar `ASSISTANT_RETENTION_DAYS` kun saqlanadi, keyin matn va shaxsiy
    ma'lumot o'chiriladi. Statistika (kanal, sana, xabarlar soni, xarajat) qoladi."""
    cutoff = timezone.now() - timedelta(days=settings.ASSISTANT_RETENTION_DAYS)
    old = Conversation.objects.filter(last_message_at__lt=cutoff, anonymized_at__isnull=True)
    count = 0
    for conversation in old.iterator():
        conversation.messages.update(text="", content=[], attachments=[])
        conversation.name = ""
        conversation.phones = {}
        conversation.telegram_username = ""
        conversation.telegram_chat_id = None
        conversation.summary = ""
        conversation.context = {}
        conversation.ip_hash = ""
        conversation.token_hash = None
        conversation.anonymized_at = timezone.now()
        conversation.save()
        count += 1
    return count
