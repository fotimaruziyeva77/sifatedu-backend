"""Google va Telegram orqali kirishni tekshirish.

Ikkala provayder ham foydalanuvchi kimligini o'zi tasdiqlaydi, shuning uchun bizda parol
saqlanmaydi. Backend faqat kelgan ma'lumot haqiqatan ham o'sha provayderdan kelganini tekshiradi.
"""

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from typing import Any

import jwt
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from jwt import PyJWKClient

from .models import SocialAccount

logger = logging.getLogger(__name__)

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
# Sabab foydalanuvchiga aytilmaydi (token eskirganmi, imzo noto'g'rimi) — logda qoladi.
GOOGLE_FAILED = _("Google javobini tekshirib bo'lmadi. Qayta urinib ko'ring.")
TELEGRAM_FAILED = _("Telegram javobini tekshirib bo'lmadi. Qayta urinib ko'ring.")
# Telegram Login Widget ma'lumoti eskirgan bo'lsa (qayta yuborilgan havola), rad etiladi.
TELEGRAM_MAX_AGE_SECONDS = 300


class SocialAuthError(Exception):
    """Token yaroqsiz yoki provayder sozlanmagan."""


@dataclass(frozen=True)
class SocialProfile:
    """Provayderdan kelgan va tekshirilgan ma'lumot."""

    provider: str
    uid: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    avatar_url: str = ""


def google_enabled() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID)


def telegram_enabled() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_USERNAME)


# Google kalitlari kamdan-kam o'zgaradi: mijoz ularni keshlaydi.
_jwk_client = PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, lifespan=3600)


def verify_google(credential: str) -> SocialProfile:
    """Google Identity Services bergan ID tokenni tekshiradi (imzo, `aud`, `iss`, muddat)."""
    if not google_enabled():
        raise SocialAuthError(_("Google orqali kirish sozlanmagan."))

    try:
        key = _jwk_client.get_signing_key_from_jwt(credential).key
        claims: dict[str, Any] = jwt.decode(
            credential,
            key,
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as exc:
        logger.info("Google ID token rad etildi: %s", exc)
        raise SocialAuthError(GOOGLE_FAILED) from exc

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise SocialAuthError(GOOGLE_FAILED)
    # Tasdiqlanmagan email boshqa odamniki bo'lishi mumkin: unga ishonmaymiz.
    email = claims.get("email", "") if claims.get("email_verified") else ""

    return SocialProfile(
        provider=SocialAccount.Provider.GOOGLE,
        uid=str(claims["sub"]),
        email=email,
        first_name=claims.get("given_name", ""),
        last_name=claims.get("family_name", ""),
        avatar_url=claims.get("picture", ""),
    )


def verify_telegram(data: dict[str, Any]) -> SocialProfile:
    """Telegram Login Widget ma'lumotini bot tokeni bilan tekshiradi (HMAC-SHA256)."""
    if not telegram_enabled():
        raise SocialAuthError(_("Telegram orqali kirish sozlanmagan."))

    received = str(data.get("hash", ""))
    fields = {key: value for key, value in data.items() if key != "hash" and value is not None}
    check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received):
        raise SocialAuthError(TELEGRAM_FAILED)

    try:
        auth_age = time.time() - int(fields.get("auth_date", 0))
    except (TypeError, ValueError) as exc:
        raise SocialAuthError(TELEGRAM_FAILED) from exc
    if auth_age > TELEGRAM_MAX_AGE_SECONDS:
        raise SocialAuthError(_("Telegram javobi eskirgan. Qayta urinib ko'ring."))

    return SocialProfile(
        provider=SocialAccount.Provider.TELEGRAM,
        uid=str(fields.get("id", "")),
        first_name=str(fields.get("first_name", "")),
        last_name=str(fields.get("last_name", "")),
        avatar_url=str(fields.get("photo_url", "")),
    )
