"""Fayllar markaz papkasida: `centers/<sxema>/...`.

Birinchi markazning (`LEGACY_STORAGE_SCHEMAS`) fayllari ko'chirilmaydi — avvalgi joyida qoladi.
Bazada kalit prefikssiz saqlanadi (`file.name`), prefiks S3 ga murojaat paytida qo'shiladi.
"""

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
