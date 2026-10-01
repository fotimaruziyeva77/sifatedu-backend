"""AI maslahatchi Telegram botda: bot menyusiga tegishli bo'lmagan har qanday matnga javob.

Botning o'zi (/start, ro'yxatdan o'tish, menyu, testlar) — `apps.bot`. U savolni `ai` navbatiga
(`tasks.telegram_answer`) beradi: javob 5–20 soniya, bot tugmalari uni kutib qolmasin.
"""

import contextlib
import logging
import re
from datetime import timedelta
from html import escape as html_escape
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.notifications import telegram as telegram_api

from .agent import respond
from .models import Conversation, Message
from .prompt import som
from .service import add_user_message, claim, release

logger = logging.getLogger(__name__)

MAX_PER_HOUR = 30
# Shuncha vaqt yozishmagan mijoz qaytsa, yangi suhbat boshlanadi.
NEW_CONVERSATION_AFTER = timedelta(days=7)
MAX_MESSAGE_LENGTH = 4000

TEXTS = {
    "uz": {
        "too_many": "Xabarlar juda ko'p bo'ldi. Biroz kutib, keyin yozing.",
        "busy": "Oldingi savolingizga javob yozyapman — bir daqiqa.",
        "free": "bepul",
        "month": "oyiga",
    },
    "ru": {
        "too_many": "Слишком много сообщений. Подождите немного и напишите снова.",
        "busy": "Пишу ответ на предыдущий вопрос — минутку.",
        "free": "бесплатно",
        "month": "в месяц",
    },
    "en": {
        "too_many": "Too many messages. Please wait a little and write again.",
        "busy": "I am still answering your previous question — one moment.",
        "free": "free",
        "month": "per month",
    },
}
BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def escape(text: str) -> str:
    """Telegram HTML uchun: faqat &, < va > qochiriladi (apostrof matnda qolaversin)."""
    return html_escape(text, quote=False)


def locale_for(language_code: str | None) -> str:
    code = (language_code or "")[:2].lower()
    return code if code in ("ru", "en") else "uz"


def card_line(card: dict[str, Any], locale: str) -> str:
    texts = TEXTS[locale]
    url = f"{settings.APP_URL.rstrip('/')}/{locale}/courses/{card['slug']}"
    if card.get("is_free"):
        price = texts["free"]
    elif card.get("price_online"):
        price = som(int(card["price_online"]))
    elif card.get("price_offline_monthly"):
        price = f"{som(int(card['price_offline_monthly']))} {texts['month']}"
    else:
        price = ""
    title = f"<b>{escape(str(card.get('title', '')))}</b>"
    return f"{title} — {escape(price)}\n{url}" if price else f"{title}\n{url}"


def render(text: str, attachments: list[dict[str, Any]], locale: str) -> str:
    """AI javobi → Telegram HTML: matn qochiriladi, **qalin** saqlanadi, kartochkalarda havola."""
    body = BOLD_RE.sub(r"<b>\1</b>", escape(text))
    parts = [body] if body else []
    parts.extend(card_line(card, locale) for card in attachments)
    return "\n\n".join(parts)[:MAX_MESSAGE_LENGTH]


def _send(chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
    try:
        telegram_api.send_message(chat_id, text, reply_markup=reply_markup)
    except (OSError, RuntimeError, telegram_api.TelegramNotConfiguredError) as exc:
        # Masalan, mijoz botni bloklagan — javobni yubora olmaymiz, suhbat baribir saqlangan.
        logger.warning("Telegram'ga yuborilmadi (chat %s): %s", chat_id, exc)


def _typing(chat_id: int) -> None:
    with contextlib.suppress(OSError, RuntimeError, telegram_api.TelegramNotConfiguredError):
        telegram_api.call("sendChatAction", {"chat_id": chat_id, "action": "typing"})


def _within_rate(chat_id: int) -> bool:
    key = f"assistant:tg:{chat_id}:{timezone.now():%Y%m%d%H}"
    cache.add(key, 0, timeout=3600)
    return cache.incr(key) <= MAX_PER_HOUR


def conversation_for(
    chat_id: int, sender: dict[str, Any], *, locale: str = "uz", fresh: bool = False
) -> Conversation:
    """Chatning ochiq suhbati. `fresh` yangisini boshlaydi — oxirgisi hali bo'sh bo'lmasa."""
    now = timezone.now()
    existing = (
        Conversation.objects.filter(
            channel=Conversation.Channel.TELEGRAM,
            telegram_chat_id=chat_id,
            anonymized_at__isnull=True,
            last_message_at__gte=now - NEW_CONVERSATION_AFTER,
        )
        .exclude(status=Conversation.Status.CLOSED)
        .order_by("-last_message_at")
        .first()
    )
    if existing is not None and (not fresh or existing.user_messages == 0):
        return existing
    name = " ".join(filter(None, [sender.get("first_name"), sender.get("last_name")]))
    return Conversation.objects.create(
        channel=Conversation.Channel.TELEGRAM,
        telegram_chat_id=chat_id,
        telegram_username=str(sender.get("username") or "")[:64],
        name=name[:100],
        locale=locale_for(locale),
        source_page="telegram",
        last_message_at=now,
    )


def send_reply(conversation: Conversation, messages: list[Message]) -> None:
    text = "\n\n".join(message.text for message in messages if message.text)
    cards = [card for message in messages for card in message.attachments]
    body = render(text, cards, conversation.locale)
    if not body or conversation.telegram_chat_id is None:
        return
    # Pastki menyu (bot tugmalari) o'z joyida qoladi: javob oddiy xabar.
    _send(conversation.telegram_chat_id, body)


def answer(chat_id: int, sender: dict[str, Any], text: str, locale: str) -> None:
    """Botga yozilgan savol: suhbatga qo'shiladi va AI javobi yuboriladi."""
    locale = locale_for(locale)
    if not _within_rate(chat_id):
        _send(chat_id, escape(TEXTS[locale]["too_many"]))
        return
    conversation = conversation_for(chat_id, sender, locale=locale)
    if not claim(conversation):
        _send(chat_id, escape(TEXTS[conversation.locale]["busy"]))
        return
    try:
        add_user_message(conversation, text)
        _typing(chat_id)
        messages = respond(conversation)
    finally:
        release(conversation)
    send_reply(conversation, messages)
