"""Server resurslari: disk va xotira.

Konteyner ichidan ham butun server ko'rinadi: `/` — Docker ma'lumotlari turgan disk (bazalar,
videolar, zaxiralar shu yerda), `/proc/meminfo` — server xotirasi. Disk to'lsa baza va videolar
yozilmay qoladi, shuning uchun oldindan ogohlantiriladi.
"""

import shutil
from pathlib import Path

from django.conf import settings

MEMINFO = Path("/proc/meminfo")


def disk_percent(path: str = "/") -> int:
    """Diskning band qismi, %."""
    usage = shutil.disk_usage(path)
    return round(usage.used * 100 / usage.total) if usage.total else 0


def memory_free_percent(meminfo: Path | None = None) -> int | None:
    """Bo'sh xotira (`MemAvailable` / `MemTotal`), %. Aniqlab bo'lmasa — None."""
    try:
        values = {}
        for line in (meminfo or MEMINFO).read_text().splitlines():
            key, _, rest = line.partition(":")
            if rest.split():
                values[key] = int(rest.split()[0])
    except (OSError, ValueError):
        return None
    total, available = values.get("MemTotal"), values.get("MemAvailable")
    if not total or available is None:
        return None
    return round(available * 100 / total)


def disk_over_limit() -> int:
    """Disk chegaradan oshgan bo'lsa — band foizi, aks holda 0 (tekshiruv o'chiq bo'lsa ham 0)."""
    if not settings.RESOURCE_CHECKS:
        return 0
    used = disk_percent()
    return used if used >= settings.DISK_ALERT_PERCENT else 0


def warnings() -> list[tuple[str, str]]:
    """Chegaradan oshgan resurslar: (ogohlantirish turi, matn)."""
    if not settings.RESOURCE_CHECKS:
        return []
    found = []
    used = disk_over_limit()
    if used:
        found.append(
            (
                "server:disk",
                f"Server diski {used}% band. Eski videolarni o'chiring yoki diskni kengaytiring.",
            )
        )
    free = memory_free_percent()
    if free is not None and free < settings.MEMORY_ALERT_FREE_PERCENT:
        found.append(
            (
                "server:memory",
                f"Serverda bo'sh xotira {free}% qoldi. Og'ir jarayonni (video) tekshiring.",
            )
        )
    return found
