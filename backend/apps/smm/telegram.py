"""Rasm albomi va matn: markaz boti orqali (kanalga ham, tasdiqlovchiga ham)."""

from collections.abc import Callable
from html import escape
from pathlib import PurePosixPath
from typing import Any

from apps.core.storage import public_storage
from apps.notifications import telegram

ALBUM_TIMEOUT = 60
CAPTION_LIMIT = telegram.CAPTION_LIMIT


class ChannelError(RuntimeError):
    """Kanal sozlanmagan yoki Telegram rad etdi."""


def html(text: str) -> str:
    return escape(text, quote=False)


def units(text: str) -> int:
    """Telegram uzunlikni UTF-16 birliklarida sanaydi (emoji — 2 ta)."""
    return len(text.encode("utf-16-le")) // 2


def clip(text: str, limit: int) -> str:
    while units(text) > limit:
        text = text[: max(0, len(text) - (units(text) - limit) // 2 - 1)]
    return text


def read(name: str) -> tuple[str, bytes, str]:
    with public_storage().open(name, "rb") as handle:
        return PurePosixPath(name).name, handle.read(), "image/jpeg"


def send_album(
    chat_id: str | int,
    images: list[str],
    caption: str = "",
    *,
    buttons: dict[str, Any] | None = None,
    on_sent: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Rasmlar (1–10) va matn. Matn rasm izohiga sig'masa yoki tugmalar bo'lsa — alohida
    xabar bo'lib keladi (albomga tugma qo'yib bo'lmaydi). Qaytadi: yuborilgan xabarlar."""
    sent: list[dict[str, Any]] = []
    separate = bool(buttons) or units(caption) > CAPTION_LIMIT
    inline = "" if separate else caption
    images = images[:10]
    if len(images) == 1:
        payload: dict[str, Any] = {"chat_id": chat_id, "parse_mode": "HTML"}
        if inline:
            payload["caption"] = inline
        result = telegram.call(
            "sendPhoto", payload, files={"photo": read(images[0])}, timeout=ALBUM_TIMEOUT
        )
        sent.append(result if isinstance(result, dict) else {})
        if on_sent:
            on_sent(sent[-1])
    elif images:
        media = []
        files = {}
        for index, name in enumerate(images):
            key = f"p{index}"
            item: dict[str, Any] = {"type": "photo", "media": f"attach://{key}"}
            if index == 0 and inline:
                item.update(caption=inline, parse_mode="HTML")
            media.append(item)
            files[key] = read(name)
        result = telegram.call(
            "sendMediaGroup",
            {"chat_id": chat_id, "media": media},
            files=files,
            timeout=ALBUM_TIMEOUT,
        )
        album = (
            [item for item in result if isinstance(item, dict)] if isinstance(result, list) else []
        )
        sent += album
        for item in album:
            if on_sent:
                on_sent(item)
    if separate and (caption or buttons):
        sent.append(
            telegram.send_message(chat_id, clip(caption, 4000) or "—", reply_markup=buttons)
        )
        if on_sent:
            on_sent(sent[-1])
    return sent
