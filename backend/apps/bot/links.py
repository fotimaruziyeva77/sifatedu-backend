"""Bir martalik havolalar: sayt → bot (testni botda boshlash) va bot → sayt (parolsiz kirish).

Token Redis'da 10 daqiqa turadi va bir marta ishlatiladi; kalit sifatida faqat uning xeshi.
Xodim (o'qituvchi, menejer, admin) uchun kirish havolasi berilmaydi — ular saytga o'zi kiradi.
"""

import hashlib
import secrets
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme

from apps.notifications import telegram
from apps.users.models import User

from .models import BotChat

TOKEN_TTL_SECONDS = 10 * 60
QUIZ_PREFIX = "q_"
REFERRAL_PREFIX = "r_"
LOGIN_PATH = "/api/v1/bot/login/{token}/"


def _key(kind: str, token: str) -> str:
    return f"bot:{kind}:{hashlib.sha256(token.encode()).hexdigest()}"


def _issue(kind: str, data: dict[str, Any]) -> str:
    token = secrets.token_urlsafe(24)
    cache.set(_key(kind, token), data, TOKEN_TTL_SECONDS)
    return token


def _take(kind: str, token: str) -> dict[str, Any] | None:
    """Tokenni bir marta ishlatadi: ikki parallel so'rovdan faqat bittasi oladi."""
    key = _key(kind, token)
    data = cache.get(key)
    if not isinstance(data, dict) or not cache.delete(key):
        return None
    return data


def base_url() -> str:
    return str(settings.APP_URL).rstrip("/")


def bot_url(payload: str = "") -> str | None:
    """`https://t.me/<bot>?start=<payload>`. Bot sozlanmagan bo'lsa — None."""
    username = telegram.bot_username()
    if not username:
        return None
    return f"https://t.me/{username}?start={payload}" if payload else f"https://t.me/{username}"


def quiz_url(user: User, quiz_id: int) -> str | None:
    """Saytdagi "Telegram'da ishlash": botda shu test boshlanadi (Telegram hali ulanmagan bo'lsa,
    bosgan odamning Telegram'i shu akkauntga ulanadi — xuddi "Telegram'ni ulash" kabi)."""
    if not telegram.bot_username():
        return None
    return bot_url(QUIZ_PREFIX + _issue("quiz", {"user": user.pk, "quiz": quiz_id}))


def take_quiz(payload: str) -> dict[str, Any] | None:
    return _take("quiz", payload.removeprefix(QUIZ_PREFIX))


def safe_path(value: str) -> str | None:
    """Faqat sayt ichidagi yo'l: boshqa saytga yo'naltirib bo'lmasin."""
    if (
        not value.startswith("/")
        or value.startswith("//")
        or not url_has_allowed_host_and_scheme(value, allowed_hosts=set())
    ):
        return None
    return value


def site_url(path: str, locale: str) -> str:
    """Sahifa (`/dashboard/...` — til prefiksi qo'shiladi) yoki API yo'li (`/api/...`)."""
    if path.startswith("/api/"):
        return f"{base_url()}{path}"
    return f"{base_url()}/{locale}{path}"


def trusted(chat: BotChat | None, user: User) -> bool:
    """Parolsiz kirish mumkinmi: faol o'quvchi va chatda uning raqami Telegram orqali tasdiqlangan
    (kontakt yuborilgan). Xodimga hech qachon."""
    return bool(
        chat is not None
        and user.is_active
        and not (user.is_staff or user.is_superuser)
        and chat.verified_phone
        and chat.verified_phone == user.phone
    )


def login_url(user: User, path: str, chat: BotChat | None = None) -> str:
    """Botdan saytga bir bosishda: parolsiz kirib, kerakli sahifa ochiladi. Havola eskirsa,
    kirish sahifasi ochiladi va keyin shu sahifaga qaytadi. Raqami tasdiqlanmagan chat va
    xodimga — oddiy havola (saytga o'zi kiradi)."""
    if not trusted(chat, user):
        return site_url(path, user.locale or "uz")
    token = _issue("login", {"user": user.pk, "next": path})
    return f"{base_url()}{LOGIN_PATH.format(token=token)}?{urlencode({'next': path})}"


def take_login(token: str) -> dict[str, Any] | None:
    return _take("login", token)
