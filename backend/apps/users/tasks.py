"""Foydalanuvchi bilan bog'liq fon vazifalari."""

import logging
import urllib.request
from io import BytesIO
from urllib.parse import urlparse

from celery import shared_task
from django.core.files.base import ContentFile
from PIL import Image
from PIL.Image import Resampling

logger = logging.getLogger(__name__)

# Rasm faqat provayderlarning o'z domenlaridan olinadi.
ALLOWED_HOSTS = ("googleusercontent.com", "telegram.org", "cdn4.telegram-cdn.org")
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 10
SIZE = 256


def _allowed(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return parsed.scheme == "https" and any(
        host == allowed or host.endswith(f".{allowed}") for allowed in ALLOWED_HOSTS
    )


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=2)
def fetch_social_avatar(user_id: int, url: str) -> None:
    """Google yoki Telegram rasmini bizning storage'ga ko'chiradi (tashqi URL ishlatilmaydi)."""
    from .models import User

    if not _allowed(url):
        logger.warning("Ijtimoiy rasm manzili ruxsat etilmagan: %s", url)
        return

    user = User.objects.filter(pk=user_id).first()
    if user is None or user.avatar:
        return

    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 - https
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        logger.warning("Ijtimoiy rasm juda katta, o'tkazib yuborildi: %s", url)
        return

    buffer = BytesIO()
    try:
        image = Image.open(BytesIO(raw))
        image.convert("RGB").resize((SIZE, SIZE), Resampling.LANCZOS).save(
            buffer, format="JPEG", quality=85
        )
    except OSError:
        logger.warning("Ijtimoiy rasmni o'qib bo'lmadi: %s", url)
        return

    user.avatar.save("avatar.jpg", ContentFile(buffer.getvalue()), save=True)
