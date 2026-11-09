"""Fayllar markaz papkasida: `centers/<sxema>/...`.

Birinchi markazning (`LEGACY_STORAGE_SCHEMAS`) fayllari ko'chirilmaydi — avvalgi joyida qoladi.
Bazada kalit prefikssiz saqlanadi (`file.name`), prefiks S3 ga murojaat paytida qo'shiladi.
"""

from typing import Any

from celery import current_task
from django.conf import settings
from django_tenants.utils import get_public_schema_name
from storages.backends.s3 import S3Storage

from .db import connection


def center_prefix() -> str:
    schema = connection.schema_name
    if schema == get_public_schema_name() or schema in settings.LEGACY_STORAGE_SCHEMAS:
        return ""
    return f"centers/{schema}/"


class CenterS3Storage(S3Storage):
    def _normalize_name(self, name: str) -> str:
        # Avval tozalanadi: `..` markaz papkasidan tashqariga olib chiqa olmaydi.
        return center_prefix() + str(super()._normalize_name(name))

    def _save(self, name: str, content: Any) -> str:
        # Fon vazifa to'xtatilmaydi: boshlangan ish (video, rasm) yarim yo'lda buzilmasin.
        if not current_task:
            from .limits import check_disk

            check_disk()
        return str(super()._save(name, content))
