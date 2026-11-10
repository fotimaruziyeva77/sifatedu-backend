"""Maxfiy kalit maydoni: Python'da ochiq matn, bazada shifrlangan.

Baza nusxasi sizib chiqsa ham kalitlarni ochish uchun ilova siri (`INTEGRATIONS_SECRET`) kerak.
"""

import base64
import hashlib
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


def _key(secret: str) -> Fernet:
    # Fernet 32 baytli urlsafe-base64 kalit kutadi, sir esa ixtiyoriy uzunlikda.
    digest = hashlib.sha256(f"center-integrations:{secret}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _fernet() -> MultiFernet:
    # Birinchi sir bilan shifrlanadi, ikkalasi bilan ochiladi: `INTEGRATIONS_SECRET` keyinroq
    # qo'shilsa ham, undan oldin `DJANGO_SECRET_KEY` bilan saqlangan kalitlar ochilaveradi.
    secrets = dict.fromkeys([settings.INTEGRATIONS_SECRET, settings.SECRET_KEY])
    return MultiFernet([_key(secret) for secret in secrets])


def seal(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def unseal(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        # Ikkala sir ham o'zgargan: kalit sozlanmagandek ko'rinadi, markaz uni qayta kiritadi.
        logger.error("Markaz kaliti ochilmadi: INTEGRATIONS_SECRET va SECRET_KEY o'zgarganmi?")
        return ""


class SecretField(models.TextField):
    def from_db_value(self, value: str | None, *_args: Any) -> str:
        return unseal(value) if value else ""

    def get_prep_value(self, value: Any) -> str:
        text = super().get_prep_value(value)
        return seal(text) if text else ""
