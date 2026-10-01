"""Telegram'ni kabinetdan ulash: bir martalik havola orqali botga "Start".

Sayt havola beradi (`https://t.me/<bot>?start=c_<token>`), foydalanuvchi botda "Start" bosadi,
Telegram botga `/start c_<token>` yuboradi. Token kimga tegishliligini Redis biladi; Telegram
akkaunti esa xabarni yuborganning o'zi — shuning uchun egalik ikki tomondan tasdiqlangan.
"""

import hashlib
import secrets
from enum import StrEnum

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.users.models import SocialAccount

from . import telegram
from .texts import text

TOKEN_TTL_SECONDS = 10 * 60
START_PREFIX = "c_"
TELEGRAM = SocialAccount.Provider.TELEGRAM


class LinkResult(StrEnum):
    LINKED = "linked"
    EXPIRED = "link_expired"
    TAKEN = "link_taken"


def _key(token: str) -> str:
    return f"tg-link:{hashlib.sha256(token.encode()).hexdigest()}"


def connect_url(user_id: int) -> str | None:
    """Botga bir martalik havola. Bot sozlanmagan bo'lsa — None."""
    username = telegram.bot_username()
    if not username:
        return None
    token = secrets.token_urlsafe(24)
    cache.set(_key(token), user_id, TOKEN_TTL_SECONDS)
    return f"https://t.me/{username}?start={START_PREFIX}{token}"


def is_link_start(payload: str) -> bool:
    return payload.startswith(START_PREFIX)


def link(payload: str, telegram_user_id: int) -> LinkResult:
    """`/start c_<token>`: tokenni tekshiradi va Telegram'ni akkauntga ulaydi."""
    key = _key(payload.removeprefix(START_PREFIX))
    user_id = cache.get(key)
    if not user_id:
        return LinkResult.EXPIRED
    cache.delete(key)  # bir martalik
    uid = str(telegram_user_id)
    owner = (
        SocialAccount.objects.filter(provider=TELEGRAM, uid=uid)
        .values_list("user_id", flat=True)
        .first()
    )
    if owner is not None and owner != user_id:
        return LinkResult.TAKEN
    try:
        with transaction.atomic():
            SocialAccount.objects.update_or_create(
                user_id=user_id,
                provider=TELEGRAM,
                defaults={"uid": uid, "notify": True, "blocked_at": None},
            )
    except IntegrityError:
        return LinkResult.TAKEN
    return LinkResult.LINKED


def reply(result: LinkResult, locale: str | None) -> str:
    return text(locale, str(result))


def set_blocked(telegram_user_id: int, *, blocked: bool) -> None:
    """Foydalanuvchi botni blokladi (`kicked`) yoki qayta yozdi — yuborish shunga qarab."""
    accounts = SocialAccount.objects.filter(provider=TELEGRAM, uid=str(telegram_user_id))
    if blocked:
        accounts.filter(blocked_at__isnull=True).update(blocked_at=timezone.now())
    else:
        accounts.filter(blocked_at__isnull=False).update(blocked_at=None)
