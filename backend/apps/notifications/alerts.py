"""Jamoaga ogohlantirish (Telegram, `TELEGRAM_ALERTS_CHAT_ID`).

To'lov yoki video xatosi haqida darhol bilish kerak, lekin bitta muammo yuzlab xabarga
aylanmasligi uchun bir xil ogohlantirish `COOLDOWN_SECONDS` ichida faqat bir marta yuboriladi.
"""

import html
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

COOLDOWN_SECONDS = 600


def alert(kind: str, text: str) -> bool:
    """Ogohlantirishni navbatga qo'yadi. Yuborilmagan bo'lsa (limit yoki sozlanmagan) — False.

    `kind` — takrorlanishni aniqlash kaliti, masalan `click:sign_failed`.
    Matnga shaxsiy ma'lumot (telefon, ism) qo'yilmaydi.
    """
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_ALERTS_CHAT_ID):
        logger.warning("Ogohlantirish (Telegram sozlanmagan): %s — %s", kind, text)
        return False
    # `add` atomik: bir vaqtda kelgan ikki xatodan faqat bittasi yuboriladi.
    if not cache.add(f"alert:{kind}", 1, timeout=COOLDOWN_SECONDS):
        return False

    from .tasks import send_alert_task

    send_alert_task.delay(f"⚠️ <b>{html.escape(kind)}</b>\n{html.escape(text)}")
    return True
