"""Markazlar: har markaz PostgreSQL'da alohida sxemada (django-tenants), bu jadvallar — `public`da.

Markaz manzil (domen) bo'yicha aniqlanadi. Sifat Edu — birinchi markaz.
"""

from typing import Any

from auditlog.context import disable_auditlog
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenants.models import DomainMixin, TenantMixin

from apps.core.models import TimeStampedModel


class Center(TenantMixin, TimeStampedModel):
    name = models.CharField(_("nomi"), max_length=200)

    class Meta:
        verbose_name = _("markaz")
        verbose_name_plural = _("markazlar")

    def __str__(self) -> str:
        return self.name

    def create_schema(self, *args: Any, **kwargs: Any) -> bool:
        # Migratsiyalar auditga yozilmaydi: so'rovdagi platforma admini yangi markazda yo'q.
        with disable_auditlog():
            return bool(super().create_schema(*args, **kwargs))


class Domain(DomainMixin):
    class Meta:
        verbose_name = _("domen")
        verbose_name_plural = _("domenlar")

    def __str__(self) -> str:
        return self.domain
