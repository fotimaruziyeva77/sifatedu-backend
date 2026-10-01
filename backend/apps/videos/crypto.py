"""HLS segmentlarini shifrlaydigan AES-128 kaliti bazada ochiq saqlanmaydi.

Kalitning o'zi Fernet bilan shifrlanadi: baza nusxasi sizib chiqsa ham videolarni ochish
uchun ilova siri (`VIDEO_KEY_SECRET`) kerak bo'ladi.
"""

import base64
import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

AES_KEY_BYTES = 16  # AES-128


def new_key() -> bytes:
    return secrets.token_bytes(AES_KEY_BYTES)


def _fernet() -> Fernet:
    # Fernet 32 baytli urlsafe-base64 kalit kutadi, sir esa ixtiyoriy uzunlikda.
    digest = hashlib.sha256(f"sifat-video-key:{settings.VIDEO_KEY_SECRET}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def seal(key: bytes) -> str:
    return _fernet().encrypt(key).decode()


def unseal(token: str) -> bytes:
    try:
        return _fernet().decrypt(token.encode())
    except InvalidToken as exc:  # Sir o'zgargan yoki yozuv buzilgan.
        raise ValueError("Video kaliti ochilmadi") from exc
