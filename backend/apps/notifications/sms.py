"""SMS yuborish: Eskiz.uz (https://notify.eskiz.uz). Matn Eskiz'da oldindan tasdiqlangan
shablonga mos bo'lishi shart, aks holda SMS yuborilmaydi."""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

API_URL = "https://notify.eskiz.uz/api"
TIMEOUT_SECONDS = 10
TOKEN_CACHE_KEY = "eskiz:token"  # noqa: S105 - kesh kaliti, parol emas
# Token 30 kun amal qiladi; ertaroq yangilanadi.
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 25


class SmsNotConfiguredError(Exception):
    """ESKIZ_EMAIL yoki ESKIZ_PASSWORD berilmagan."""


def send_sms(phone: str, text: str) -> None:
    """SMS yuboradi. Tarmoq yoki provayder xatosida istisno ko'taradi (Celery qayta urinadi)."""
    if settings.SMS_DRY_RUN:
        # Faqat local va testlar: kod logdan o'qiladi.
        logger.warning("SMS (dry-run) %s: %s", phone, text)
        return
    if not settings.ESKIZ_EMAIL or not settings.ESKIZ_PASSWORD:
        raise SmsNotConfiguredError

    payload = {"mobile_phone": phone.lstrip("+"), "message": text, "from": settings.ESKIZ_FROM}
    status, body = _post("/message/sms/send", payload, _token())
    if status == 401:
        status, body = _post("/message/sms/send", payload, _token(refresh=True))
    if status >= 400:
        raise RuntimeError(f"Eskiz javobi {status}: {body.get('message', '')}")


def _token(*, refresh: bool = False) -> str:
    if not refresh:
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return str(cached)
    status, body = _post(
        "/auth/login", {"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD}
    )
    token = body.get("data", {}).get("token") if status < 400 else None
    if not token:
        raise RuntimeError(f"Eskiz'ga kirib bo'lmadi: {status}")
    cache.set(TOKEN_CACHE_KEY, token, TOKEN_TTL_SECONDS)
    return str(token)


def _post(path: str, data: dict[str, str], token: str | None = None) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(  # noqa: S310 - URL qat'iy https
        f"{API_URL}{path}",
        data=urllib.parse.urlencode(data).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.status, _json(response.read())
    except urllib.error.HTTPError as error:
        return error.code, _json(error.read())


def _json(raw: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or b"{}")
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
