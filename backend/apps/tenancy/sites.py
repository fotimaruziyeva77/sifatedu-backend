"""Hozirgi markazning tashqi ko'rinishi: nomi va sayt manzili.

Matnlar birinchi markaz nomi bilan yozilgan: boshqa markazda nom almashtiriladi (`rebrand`).
"""

from django.conf import settings
from django_tenants.utils import get_public_schema_name

from .access import current_center
from .db import connection

FLAGSHIP_NAME = "Sifat Edu"
FLAGSHIP_KIDS = "SIFAT Kids"
KIDS = "Kids"


def is_platform() -> bool:
    return bool(connection.schema_name == get_public_schema_name())


def is_flagship() -> bool:
    """Birinchi markaz: hozirgi landing, «SIFAT» logosi, Google bilan kirish shu markazda."""
    return bool(connection.schema_name == settings.FIRST_CENTER_SCHEMA)


def center_name() -> str:
    if is_platform():
        return str(settings.PLATFORM_NAME)
    center = current_center()
    return center.name if center else str(settings.PLATFORM_NAME)


def site_url() -> str:
    """Markaz saytining manzili (oxirida `/` yo'q). Bot, Click va xabarlardagi havolalar uchun."""
    center = current_center()
    domain = None
    if center is not None:
        domain = center.domains.filter(is_primary=True).values_list("domain", flat=True).first()
    return f"{settings.SITE_SCHEME}://{domain or settings.PLATFORM_DOMAIN}{settings.SITE_PORT}"


def rebrand(text: str) -> str:
    """Matndagi birinchi markaz nomi o'rniga hozirgi markaz nomi."""
    if is_flagship():
        return text
    return text.replace(FLAGSHIP_NAME, center_name()).replace(FLAGSHIP_KIDS, KIDS)
