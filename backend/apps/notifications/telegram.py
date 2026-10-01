"""Telegram Bot API: arizalar, ogohlantirishlar, xabarnomalar va AI maslahatchi boti."""

import hashlib
import json
import logging
import mimetypes
import secrets
import urllib.error
import urllib.request
from pathlib import PurePosixPath
from typing import Any

from django.conf import settings
from django.core.cache import cache

from apps.core.storage import public_storage

logger = logging.getLogger(__name__)

API_URL = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT_SECONDS = 10
BOT_USERNAME_KEY = "telegram:bot-username"
BOT_USERNAME_TTL = 24 * 60 * 60
BOT_USERNAME_RETRY = 5 * 60
# Yuklangan rasmning Telegram'dagi ID si: keyingi yuborishlarda fayl qayta yuklanmaydi.
PHOTO_KEY = "telegram:photo:{}"
PHOTO_TTL = 30 * 24 * 60 * 60
CAPTION_LIMIT = 1024


class TelegramNotConfiguredError(Exception):
    """Token yoki chat ID berilmagan."""


class TelegramError(RuntimeError):
    """Bot API xatosi. `retry_after` — 429 javobida necha soniya kutish kerakligi."""

    def __init__(self, code: int, description: str, retry_after: int | None = None) -> None:
        super().__init__(f"Telegram javobi {code}: {description}")
        self.code = code
        self.description = description
        self.retry_after = retry_after

    @property
    def unreachable(self) -> bool:
        """Bu odamga yozib bo'lmaydi: botni bloklagan, ruxsat bermagan yoki akkaunti o'chgan."""
        return self.code == 403 or (
            self.code == 400 and "chat not found" in self.description.lower()
        )


def _error(body: dict[str, Any], code: int) -> TelegramError:
    retry_after = (body.get("parameters") or {}).get("retry_after")
    return TelegramError(
        int(body.get("error_code") or code),
        str(body.get("description") or "xato"),
        int(retry_after) if retry_after else None,
    )


def _multipart(
    fields: dict[str, Any], files: dict[str, tuple[str, bytes, str]]
) -> tuple[bytes, str]:
    """Fayl yuborish uchun `multipart/form-data` (tugmalar JSON qatori bo'lib ketadi)."""
    boundary = secrets.token_hex(16)
    parts: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        content = value if isinstance(value, str) else json.dumps(value)
        parts += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            content.encode(),
        ]
    for name, (filename, data, content_type) in files.items():
        parts += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode(),
            f"Content-Type: {content_type}".encode(),
            b"",
            data,
        ]
    parts += [f"--{boundary}--".encode(), b""]
    return b"\r\n".join(parts), f"multipart/form-data; boundary={boundary}"


def call(
    method: str,
    payload: dict[str, Any],
    *,
    timeout: float = TIMEOUT_SECONDS,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> Any:
    """Bot API metodini chaqiradi va `result`ni qaytaradi. Xatoda istisno ko'taradi:
    Telegram rad etsa — `TelegramError`, tarmoq ishlamasa — `OSError`."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise TelegramNotConfiguredError
    if files:
        data, content_type = _multipart(payload, files)
    else:
        data, content_type = json.dumps(payload).encode(), "application/json"
    request = urllib.request.Request(  # noqa: S310 - URL qat'iy https
        API_URL.format(token=token, method=method),
        data=data,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        # 4xx javobining tanasida sabab bor (masalan, "bot was blocked by the user").
        try:
            parsed = json.loads(error.read() or b"{}")
        except ValueError:
            parsed = {}
        raise _error(parsed if isinstance(parsed, dict) else {}, error.code) from error
    if not body.get("ok"):
        raise _error(body, 0)
    return body.get("result")


def send_message(
    chat_id: str | int, text: str, *, reply_markup: dict[str, Any] | None = None
) -> dict[str, Any]:
    """HTML formatidagi xabar yuboradi va uni qaytaradi (`message_id` — keyin tahrirlash uchun).
    Xatoda istisno ko'taradi (Celery qayta urinadi)."""
    if not chat_id:
        raise TelegramNotConfiguredError
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    result = call("sendMessage", payload)
    return result if isinstance(result, dict) else {}


def edit_message(
    chat_id: int, message_id: int, text: str, *, reply_markup: dict[str, Any] | None = None
) -> None:
    """Xabar matni va tugmalarini almashtiradi. O'zgarish yo'q bo'lsa, Telegram xatosi yutiladi."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        call("editMessageText", payload)
    except TelegramError as exc:
        if "message is not modified" not in exc.description:
            raise


def answer_callback(callback_id: str, text: str = "", *, alert: bool = False) -> None:
    """Tugma bosilganini tasdiqlaydi (Telegram'dagi "kutish" belgisi yo'qoladi)."""
    payload: dict[str, Any] = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text[:200]
        payload["show_alert"] = alert
    try:
        call("answerCallbackQuery", payload)
    except (OSError, RuntimeError, TelegramNotConfiguredError) as exc:
        # Eskirgan tugma (15 daqiqadan eski) — javob berib bo'lmaydi, bu xato emas.
        logger.info("Tugma javobi yuborilmadi: %s", exc)


def _photo_key(image_name: str) -> str:
    return PHOTO_KEY.format(hashlib.sha256(image_name.encode()).hexdigest()[:32])


def _upload_photo(payload: dict[str, Any], image_name: str) -> dict[str, Any]:
    with public_storage().open(image_name, "rb") as handle:
        content = handle.read()
    filename = PurePosixPath(image_name).name
    content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
    result = call("sendPhoto", payload, files={"photo": (filename, content, content_type)})
    message = result if isinstance(result, dict) else {}
    sizes = message.get("photo") or []
    if sizes:
        cache.set(_photo_key(image_name), sizes[-1]["file_id"], PHOTO_TTL)
    return message


def send_photo(
    chat_id: str | int,
    image_name: str,
    *,
    caption: str = "",
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ochiq storage'dagi rasmni yuboradi: birinchi marta fayl yuklanadi, keyin Telegram
    bergan ID bilan (tez, trafik sarflanmaydi)."""
    payload: dict[str, Any] = {"chat_id": chat_id, "parse_mode": "HTML"}
    if caption:
        payload["caption"] = caption[:CAPTION_LIMIT]
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    file_id = cache.get(_photo_key(image_name))
    if file_id:
        try:
            result = call("sendPhoto", {**payload, "photo": file_id})
            return result if isinstance(result, dict) else {}
        except TelegramError as exc:
            # Bot almashgan bo'lsa, eski ID ishlamaydi — faylni qayta yuklaymiz.
            if exc.code != 400:
                raise
            cache.delete(_photo_key(image_name))
    return _upload_photo(payload, image_name)


def send_rich(
    chat_id: str | int,
    text: str,
    *,
    image: str = "",
    reply_markup: dict[str, Any] | None = None,
) -> None:
    """Matn (va rasm bo'lsa — rasm). Matn rasm izohiga sig'masa, rasm alohida, matn keyin."""
    if not image:
        send_message(chat_id, text, reply_markup=reply_markup)
        return
    if len(text) <= CAPTION_LIMIT:
        send_photo(chat_id, image, caption=text, reply_markup=reply_markup)
        return
    send_photo(chat_id, image)
    send_message(chat_id, text, reply_markup=reply_markup)


def bot_username() -> str:
    """Bot nomi (@siz): sozlamadan yoki `getMe` orqali (bir kun keshlanadi). Bo'lmasa — "".

    Telegram javob bermasa, 5 daqiqa qayta so'ralmaydi: dars sahifalari har safar 10 soniya
    kutib qolmasin."""
    if settings.TELEGRAM_BOT_USERNAME:
        return str(settings.TELEGRAM_BOT_USERNAME).lstrip("@")
    if not settings.TELEGRAM_BOT_TOKEN:
        return ""
    cached = cache.get(BOT_USERNAME_KEY)
    if cached is not None:
        return str(cached)
    try:
        me = call("getMe", {})
    except (OSError, RuntimeError, TelegramNotConfiguredError) as exc:
        logger.warning("Bot nomini olib bo'lmadi: %s", exc)
        cache.set(BOT_USERNAME_KEY, "", BOT_USERNAME_RETRY)
        return ""
    username = str((me or {}).get("username") or "")
    cache.set(BOT_USERNAME_KEY, username, BOT_USERNAME_TTL if username else BOT_USERNAME_RETRY)
    return username
