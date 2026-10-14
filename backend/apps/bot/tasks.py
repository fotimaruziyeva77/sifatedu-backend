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


@shared_task(acks_late=False, soft_time_limit=50, time_limit=60)
def save_profile_photo(chat_id: int, user_id: int, file_id: str) -> None:
    """Botga yuborilgan selfi o'quvchi rasmi bo'ladi (`profile.store_photo`)."""
    from . import profile

    profile.store_photo(chat_id, user_id, file_id)


@shared_task(acks_late=False)
def push_profile(user_id: int) -> None:
    """Guruhga qo'shilgan o'quvchiga botda «Profilni to'ldiring» (Telegram ulangan bo'lsa)."""
    from apps.users.models import User

    from . import profile

    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is not None and profile.wanted(user):
        profile.push(user)
