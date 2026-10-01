import logging
from typing import Any

from celery import Task, shared_task

from apps.notifications import telegram

from . import news, router

logger = logging.getLogger(__name__)

NEWS_RETRIES = 5


# Qayta bajarilmaydi (acks_late=False): test javobi ikki marta yozilgandan ko'ra, o'quvchi
# tugmani qayta bosgani yaxshi.
@shared_task(acks_late=False, soft_time_limit=50, time_limit=60)
def handle_update(update: dict[str, Any]) -> None:
    """Telegram botga kelgan yangilanish (xabar, tugma, bot holati)."""
    router.handle_update(update)


# `bulk` navbati: soniyasiga bitta to'plam (25 ta) — Telegram limiti 30 xabar/soniya.
@shared_task(bind=True, rate_limit="1/s", max_retries=NEWS_RETRIES)
def deliver_news(self: Task, broadcast_id: int, chat_ids: list[int]) -> str:
    """Yangilik bot foydalanuvchilariga. Qayta urinishda yuborilganlar o'tkazib yuboriladi."""
    try:
        sent, failed = news.deliver(broadcast_id, chat_ids)
    except telegram.TelegramError as exc:
        # 429: Telegram aytgan vaqtcha kutamiz.
        raise self.retry(countdown=exc.retry_after or 5, exc=exc) from exc
    except OSError as exc:
        if self.request.retries >= NEWS_RETRIES:
            logger.error("Yangilik bot foydalanuvchilariga yetkazilmadi (tarmoq): %s", exc)
            return "failed"
        raise self.retry(countdown=5 * 2**self.request.retries, exc=exc) from exc
    return f"{sent}/{failed}"
