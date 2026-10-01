"""HLS playlist'larini har so'rovda qayta yasash.

Segmentlar yopiq bucket'da turadi, shuning uchun playlist ichidagi havolalar qisqa muddatli
imzolangan URL'lar bilan almashtiriladi. Shifrlash kaliti esa backend orqali beriladi:
uni faqat kursga kirish huquqi bor foydalanuvchi oladi.
"""

import re
from typing import Any

from django.conf import settings

from . import s3
from .models import VideoAsset

PLAYLIST_CONTENT_TYPE = "application/vnd.apple.mpegurl"
_KEY_URI = re.compile(r'URI="[^"]*"')


def variants(video: VideoAsset) -> list[dict[str, Any]]:
    return [item for item in (video.variants or []) if item.get("playlist")]


def master(video: VideoAsset, rendition_url: str) -> str:
    """Sifatlar ro'yxati. `rendition_url` — `{name}` o'rni bor shablon."""
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for item in sorted(variants(video), key=lambda entry: int(entry["height"])):
        height = int(item["height"])
        width = int(item.get("width") or 0)
        resolution = f",RESOLUTION={width}x{height}" if width else ""
        lines.append(f"#EXT-X-STREAM-INF:BANDWIDTH={int(item['bandwidth'])}{resolution}")
        lines.append(rendition_url.format(name=f"{height}p"))
    return "\n".join(lines) + "\n"


def rendition(video: VideoAsset, name: str, key_url: str) -> str | None:
    """Saqlangan playlist'ni imzolangan segment havolalari bilan qaytaradi."""
    item = next(
        (entry for entry in variants(video) if entry["playlist"].startswith(f"{name}/")), None
    )
    if item is None:
        return None

    key = f"{video.hls_prefix}/{item['playlist']}"
    body = s3.internal().get_object(Bucket=s3.bucket(), Key=key)["Body"].read().decode()
    ttl = settings.HLS_SIGNED_URL_TTL_SEC
    folder = item["playlist"].rsplit("/", 1)[0]

    out: list[str] = []
    for line in body.splitlines():
        text = line.strip()
        if text.startswith("#EXT-X-KEY"):
            out.append(_KEY_URI.sub(f'URI="{key_url}"', text))
        elif text and not text.startswith("#"):
            out.append(s3.sign_get(f"{video.hls_prefix}/{folder}/{text}", ttl))
        else:
            out.append(text)
    return "\n".join(out) + "\n"
