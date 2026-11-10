"""Testlar uchun: hozirgi markaz kalitlarini beradi."""

from typing import Any

from .models import Integrations


def set_keys(**fields: Any) -> None:
    Integrations.objects.update_or_create(pk=1, defaults=fields)
