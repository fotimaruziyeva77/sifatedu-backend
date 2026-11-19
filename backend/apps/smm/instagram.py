"""Instagram API with Instagram Login: o'z professional hisobimizga rasm va karusel chiqarish.

Rasmiy hujjat: developers.facebook.com/docs/instagram-platform/content-publishing
- host `graph.instagram.com`, ruxsatlar `instagram_business_basic`,
  `instagram_business_content_publish` (Facebook sahifa kerak emas);
- rasm: JPEG, 4:5 … 1.91:1, ≤ 8 MB, Meta yuklab oladigan ochiq HTTPS havola;
- karusel: har rasm — `is_carousel_item=true` konteyner, keyin `media_type=CAROUSEL` + `children`
  (≤ 20), izoh faqat ota konteynerda; so'ng `media_publish`;
- token 60 kun yashaydi, 24 soatdan keyin `refresh_access_token` bilan yangilanadi.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

HOST = "https://graph.instagram.com"
TIMEOUT = 30
CAPTION_LIMIT = 2200
MAX_ITEMS = 20
# Rasm konteyneri odatda darhol tayyor bo'ladi; video bo'lsa — kutish kerak.
POLL_ATTEMPTS = 8
POLL_DELAY = 5.0


class InstagramError(RuntimeError):
    """Instagram rad etdi yoki javob bermadi. Matnda token bo'lmaydi. `code` — Meta xato kodi
    (190 — token yaroqsiz yoki muddati o'tgan)."""

    def __init__(self, message: str, *, code: int = 0) -> None:
        super().__init__(message)
        self.code = code

    @property
    def auth(self) -> bool:
        return self.code == 190


def _url(path: str, *, versioned: bool = True) -> str:
    version = f"/{settings.SMM_IG_API_VERSION}" if versioned else ""
    return f"{HOST}{version}/{path.lstrip('/')}"


def request(
    method: str, path: str, params: dict[str, Any], token: str, *, versioned: bool = True
) -> dict[str, Any]:
    fields = {key: str(value) for key, value in params.items() if value is not None}
    fields["access_token"] = token
    encoded = urllib.parse.urlencode(fields)
    url = _url(path, versioned=versioned)
    if method == "GET":
        req = urllib.request.Request(f"{url}?{encoded}", method="GET")  # noqa: S310
    else:
        req = urllib.request.Request(  # noqa: S310 - URL qat'iy https
            url,
            data=encoded.encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:  # noqa: S310
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read() or b"{}")
        except ValueError:
            body = {}
        detail = (body.get("error") or {}) if isinstance(body, dict) else {}
        message = str(detail.get("message") or f"HTTP {error.code}")
        raw = str(detail.get("code") or "")
        raise InstagramError(
            f"Instagram: {message}", code=int(raw) if raw.isdigit() else 0
        ) from None
    except (OSError, ValueError) as exc:
        raise InstagramError(f"Instagram bilan aloqa yo'q: {exc.__class__.__name__}") from None
    if not isinstance(body, dict):
        raise InstagramError("Instagram javobi tushunarsiz.")
    return body


def me(token: str) -> tuple[str, str]:
    """(IG user id, username). Hujjatdagi javob `{"data": [{...}]}`, oddiy obyekt ham bo'lishi
    mumkin."""
    body = request("GET", "me", {"fields": "user_id,username"}, token)
    data = body.get("data")
    item = data[0] if isinstance(data, list) and data else body
    user_id = str(item.get("user_id") or item.get("id") or "")
    if not user_id:
        raise InstagramError("Instagram hisob ID sini qaytarmadi.")
    return user_id, str(item.get("username") or "")


def refresh(token: str) -> str:
    body = request(
        "GET",
        "refresh_access_token",
        {"grant_type": "ig_refresh_token"},
        token,
        versioned=False,
    )
    fresh = str(body.get("access_token") or "")
    if not fresh:
        raise InstagramError("Instagram yangi token bermadi.")
    return fresh


def wait_ready(container: str, token: str, sleep: Callable[[float], None] = time.sleep) -> None:
    for attempt in range(POLL_ATTEMPTS):
        state = status(container, token)
        if state in ("FINISHED", "PUBLISHED"):
            return
        if state in ("ERROR", "EXPIRED"):
            raise InstagramError(f"Instagram rasmni qabul qilmadi ({state}).")
        if attempt < POLL_ATTEMPTS - 1:
            sleep(POLL_DELAY)
    raise InstagramError("Instagram rasmni vaqtida tayyorlamadi.")


def created(body: dict[str, Any]) -> str:
    value = str(body.get("id") or "")
    if not value:
        raise InstagramError("Instagram konteyner yaratmadi.")
    return value


def status(container: str, token: str) -> str:
    return str(request("GET", container, {"fields": "status_code"}, token).get("status_code"))


def prepare(
    user_id: str,
    token: str,
    image_urls: list[str],
    caption: str,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Rasm yoki karusel konteyneri (hali chiqmagan). Qaytadi: konteyner ID si."""
    urls = image_urls[:MAX_ITEMS]
    if not urls:
        raise InstagramError("Rasm yo'q.")
    caption = caption[:CAPTION_LIMIT]
    media = f"{user_id}/media"
    if len(urls) == 1:
        container = created(
            request("POST", media, {"image_url": urls[0], "caption": caption}, token)
        )
    else:
        children = [
            created(request("POST", media, {"image_url": url, "is_carousel_item": "true"}, token))
            for url in urls
        ]
        for child in children:
            wait_ready(child, token, sleep)
        container = created(
            request(
                "POST",
                media,
                {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption},
                token,
            )
        )
    wait_ready(container, token, sleep)
    return container


def publish(user_id: str, token: str, container: str) -> str:
    """Tayyor konteynerni chiqaradi. Qaytadi: Instagram'dagi post ID si."""
    result = request("POST", f"{user_id}/media_publish", {"creation_id": container}, token)
    media_id = str(result.get("id") or "")
    if not media_id:
        raise InstagramError("Instagram post ID sini qaytarmadi.")
    return media_id


def permalink(media_id: str, token: str) -> str:
    try:
        return str(request("GET", media_id, {"fields": "permalink"}, token).get("permalink") or "")
    except InstagramError as exc:
        logger.info("Instagram havolasi olinmadi: %s", exc)
        return ""
