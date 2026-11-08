from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.tenancy.services import ensure_center, ensure_platform


class Command(BaseCommand):
    help = "Bo'sh bazada platforma va birinchi markazni yaratadi (local va E2E uchun)."

    def handle(self, *args: Any, **options: Any) -> None:
        ensure_platform(settings.PLATFORM_DOMAIN)
        center = ensure_center(
            settings.FIRST_CENTER_SCHEMA, settings.FIRST_CENTER_NAME, settings.FIRST_CENTER_DOMAINS
        )
        self.stdout.write(f"Markaz tayyor: {center.schema_name}")
