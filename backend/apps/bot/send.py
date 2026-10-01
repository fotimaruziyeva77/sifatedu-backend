"""Botdan xabar yuborish: tugmalar, local muhitdagi havolalar va Telegram xatolari.

Javob yuborilmasa (tarmoq, bot bloklangan), yangilanish qayta ishlanmaydi: test javobi ikki marta
yozilgandan ko'ra, o'quvchi tugmani qayta bosgani yaxshi. Xato logga yoziladi.
"""

import logging
from html import escape as html_escape
from typing import Any

from django.utils import timezone

from apps.notifications import linking, telegram

from .models import BotChat

logger = logging.getLogger(__name__)

Rows = list[list[dict[str, Any]]]
MESSAGE_LIMIT = 4000


def escape(value: object) -> str:
    """Telegram HTML uchun: faqat &, < va > (apostrof matnda qolsin)."""
    return html_escape(str(value), quote=False)


def button(text: str, data: str) -> dict[str, Any]:
    return {"text": text, "callback_data": data}


def link(text: str, url: str) -> dict[str, Any]:
    return {"text": text, "url": url}


def rows_of(buttons: list[dict[str, Any]], size: int) -> Rows:
    return [buttons[start : start + size] for start in range(0, len(buttons), size)]


def inline(text: str, rows: Rows | None) -> tuple[str, dict[str, Any] | None]:
    """Inline tugmalar. Telegram tugmada localhost havolani qabul qilmaydi (local muhit) —
    bunday havola matn oxiriga yoziladi."""
    kept: Rows = []
    extra: list[str] = []
    for row in rows or []:
        usable = []
        for item in row:
            url = item.get("url")
            if url and not str(url).startswith("https://"):
                extra.append(f"{escape(item['text'])}: {escape(url)}")
                continue
            usable.append(item)
        if usable:
            kept.append(usable)
    if extra:
        text = f"{text}\n\n" + "\n".join(extra)
    return text, ({"inline_keyboard": kept} if kept else None)


def mark_blocked(chat_id: int) -> None:
    BotChat.objects.filter(chat_id=chat_id, blocked_at__isnull=True).update(
        blocked_at=timezone.now()
    )
    linking.set_blocked(chat_id, blocked=True)


def _failed(chat_id: int, exc: Exception) -> None:
    if isinstance(exc, telegram.TelegramError) and exc.unreachable:
        mark_blocked(chat_id)
    logger.warning("Bot javobi yuborilmadi (chat %s): %s", chat_id, exc)


def send(
    chat_id: int,
    text: str,
    rows: Rows | None = None,
    *,
    keyboard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Xabar. `keyboard` — pastki menyu (reply keyboard), `rows` — xabar ostidagi tugmalar.
    Qaytadi: yuborilgan xabar (`message_id`) yoki xatoda bo'sh lug'at."""
    body, markup = inline(text, rows)
    if keyboard is not None:
        markup = keyboard
    try:
        return telegram.send_message(chat_id, body[:MESSAGE_LIMIT], reply_markup=markup)
    except (OSError, RuntimeError, telegram.TelegramNotConfiguredError) as exc:
        _failed(chat_id, exc)
        return {}


def edit(chat_id: int, message_id: int | None, text: str, rows: Rows | None = None) -> None:
    """Xabarni joyida yangilaydi (tanlangan variantlar, javob natijasi)."""
    if not message_id:
        return
    body, markup = inline(text, rows)
    try:
        telegram.edit_message(
            chat_id,
            message_id,
            body[:MESSAGE_LIMIT],
            reply_markup=markup or {"inline_keyboard": []},
        )
    except (OSError, RuntimeError, telegram.TelegramNotConfiguredError) as exc:
        _failed(chat_id, exc)


def split(blocks: list[str], limit: int = MESSAGE_LIMIT) -> list[str]:
    """Bloklarni Telegram chegarasiga sig'adigan xabarlarga bo'ladi (blok o'rtasidan emas)."""
    messages: list[str] = []
    current = ""
    for block in blocks:
        block = block[:limit]
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > limit:
            messages.append(current)
            current = block
        else:
            current = candidate
    if current:
        messages.append(current)
    return messages
