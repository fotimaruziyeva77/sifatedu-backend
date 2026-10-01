"""Majburiy obuna: botdan foydalanish uchun kanal(lar)ga a'zo bo'lish (faqat botda, saytda emas).

A'zolik `getChatMember` bilan tekshiriladi, o'tgani 30 daqiqa eslab qolinadi. Bot kanalda
administrator bo'lmasa, Telegram a'zolikni aytmaydi: bunda obuna so'ralmaydi (o'quvchilar
to'xtab qolmasin) va admin bosh sahifasidagi "muammolar"da ogohlantirish chiqadi.
"""

import logging
from typing import Any

from django.core.cache import cache

from apps.notifications import telegram

from .models import RequiredChannel

logger = logging.getLogger(__name__)

MEMBER_STATUSES = frozenset({"creator", "administrator", "member"})
PASSED_TTL = 30 * 60
PROBLEM_TTL = 24 * 60 * 60
# Bot administrator qilingan kanallar: yopiq kanal ID sini taklif havolasidan bilib bo'lmaydi,
# shuning uchun Telegram bot qo'shilganda yuborgan xabardan olinadi va admin'da ko'rsatiladi.
ADMIN_CHATS_KEY = "bot:admin-chats"


def _passed_key(chat_id: int) -> str:
    return f"bot:sub:{chat_id}"


def _problem_key(channel_id: int) -> str:
    return f"bot:channel-problem:{channel_id}"


def active_channels() -> list[RequiredChannel]:
    return list(RequiredChannel.objects.filter(is_active=True))


def is_member(channel: RequiredChannel, user_id: int) -> bool:
    """A'zomi. Tekshirib bo'lmasa (bot admin emas, kanal topilmadi, tarmoq) — ha deb hisoblanadi."""
    try:
        member = telegram.call("getChatMember", {"chat_id": channel.chat, "user_id": user_id})
    except telegram.TelegramError as exc:
        cache.set(_problem_key(channel.pk), exc.description[:200], PROBLEM_TTL)
        logger.warning("Kanal a'zoligini tekshirib bo'lmadi (%s): %s", channel.chat, exc)
        return True
    except (OSError, telegram.TelegramNotConfiguredError) as exc:
        logger.warning("Kanal a'zoligini tekshirib bo'lmadi (%s): %s", channel.chat, exc)
        return True
    cache.delete(_problem_key(channel.pk))
    status = (member or {}).get("status")
    if status == "restricted":
        return bool(member.get("is_member"))
    return status in MEMBER_STATUSES


def missing(chat_id: int, *, fresh: bool = False) -> list[RequiredChannel]:
    """Hali obuna bo'linmagan kanallar. `fresh` — "Obuna bo'ldim" bosilganda qaytadan so'raladi."""
    channels = active_channels()
    if not channels:
        return []
    if not fresh and cache.get(_passed_key(chat_id)):
        return []
    lacking = [channel for channel in channels if not is_member(channel, chat_id)]
    if not lacking:
        cache.set(_passed_key(chat_id), 1, PASSED_TTL)
    return lacking


def remember(chat: dict[str, Any], status: str) -> None:
    """Bot kanalga administrator qilindi (yoki chiqarildi) — ro'yxat admin formasi uchun."""
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return
    known = dict(cache.get(ADMIN_CHATS_KEY) or {})
    if status in ("administrator", "creator"):
        known[str(chat_id)] = {
            "title": str(chat.get("title") or ""),
            "type": str(chat.get("type") or ""),
        }
    else:
        known.pop(str(chat_id), None)
    cache.set(ADMIN_CHATS_KEY, known, None)
    logger.info("Bot holati «%s» (%s): %s", chat.get("title"), chat_id, status)


def admin_channels() -> list[tuple[int, str]]:
    """Bot administrator bo'lgan kanallar: (ID, nomi)."""
    known = cache.get(ADMIN_CHATS_KEY) or {}
    return [
        (int(chat_id), str(item.get("title") or ""))
        for chat_id, item in known.items()
        if item.get("type") == "channel"
    ]


def problem(channel_id: int) -> str:
    """Oxirgi tekshiruvdagi xato (bot kanalda admin emas va h.k.). Muammo yo'q — bo'sh qator."""
    return str(cache.get(_problem_key(channel_id)) or "")


def problems() -> list[tuple[RequiredChannel, str]]:
    """Admin uchun: bot a'zolikni tekshira olmayotgan faol kanallar va sababi."""
    found = []
    for channel in active_channels():
        note = problem(channel.pk)
        if note:
            found.append((channel, note))
    return found
