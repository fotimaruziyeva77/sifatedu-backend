"""Tizim xatolari hisoblagichi: har bir ERROR log yozuvi kun va bo'lim bo'yicha sanaladi.

Tafsilot (stack trace) Sentry'da; bu yerda faqat son — admin bosh sahifasi va kunlik hisobot
"bugun qayerda muammo bo'ldi"ni ko'rsatishi uchun. Redis'da 40 kun turadi.
"""

import contextlib
import logging
from collections.abc import Iterable
from datetime import date

from django.core.cache import cache
from django.utils import timezone

TTL_SECONDS = 40 * 24 * 60 * 60

# Logger nomi → bo'lim. Birinchi mos kelgan prefiks olinadi.
AREAS: tuple[tuple[str, str], ...] = (
    ("django.request", "server"),
    ("django.server", "server"),
    ("apps.payments", "payments"),
    ("apps.notifications", "messages"),
    ("apps.users", "auth"),
    ("apps.assistant", "ai"),
    ("apps.videos", "video"),
    ("celery", "tasks"),
)
AREA_NAMES = (*dict.fromkeys(area for _prefix, area in AREAS), "other")


def area_for(logger_name: str) -> str:
    for prefix, area in AREAS:
        if logger_name == prefix or logger_name.startswith(f"{prefix}."):
            return area
    return "other"


def _key(day: date, area: str) -> str:
    return f"stats:errors:{day:%Y%m%d}:{area}"


def count_error(area: str, day: date | None = None) -> None:
    key = _key(day or timezone.localdate(), area)
    cache.add(key, 0, timeout=TTL_SECONDS)
    cache.incr(key)


def error_counts(days: Iterable[date]) -> dict[str, int]:
    """Bo'limlar bo'yicha xatolar soni (faqat noldan kattalari, kamayish tartibida)."""
    keys = {_key(day, area): area for day in days for area in AREA_NAMES}
    totals: dict[str, int] = {}
    for key, value in cache.get_many(list(keys)).items():
        area = keys[key]
        totals[area] = totals.get(area, 0) + int(value)
    return dict(sorted(((a, n) for a, n in totals.items() if n), key=lambda item: -item[1]))


class ErrorCounter(logging.Handler):
    """Root logger'ga ulanadi (settings.LOGGING va Celery worker'da)."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)

    def emit(self, record: logging.LogRecord) -> None:
        # Hisoblagich asosiy ishni hech qachon buzmasin (masalan, Redis ishlamasa).
        with contextlib.suppress(Exception):
            count_error(area_for(record.name))
