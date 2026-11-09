"""Markazlar: har markaz PostgreSQL'da alohida sxemada (django-tenants), bu jadvallar — `public`da.

Markaz manzil (domen) bo'yicha aniqlanadi. Sifat Edu — birinchi markaz.
"""

from typing import Any

from auditlog.context import disable_auditlog
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_tenants.models import DomainMixin, TenantMixin

from apps.core.models import TimeStampedModel

from .sections import Feature, with_dependencies


def _feature_list(label: Any) -> ArrayField:
    return ArrayField(
        models.CharField(max_length=20, choices=Feature.choices),
        verbose_name=label,
        default=list,
        blank=True,
    )


class Plan(TimeStampedModel):
    """Tarif: qaysi bo'limlar ochiq va cheklovlar. Platforma panelida tahrirlanadi."""

    name = models.CharField(_("nomi"), max_length=100, unique=True)
    price = models.PositiveIntegerField(_("oylik narx, so'm"), default=0)
    features = _feature_list(_("bo'limlar"))
    max_students = models.PositiveIntegerField(
        _("o'quvchilar"), null=True, blank=True, help_text=_("Bo'sh — cheksiz.")
    )
    max_staff = models.PositiveIntegerField(
        _("xodimlar"), null=True, blank=True, help_text=_("Bo'sh — cheksiz.")
    )
    max_disk_gb = models.PositiveIntegerField(
        _("disk, GB"), null=True, blank=True, help_text=_("Bo'sh — cheksiz.")
    )
    grace_days = models.PositiveSmallIntegerField(_("muddat tugagach muhlat, kun"), default=7)
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("tarif")
        verbose_name_plural = _("tariflar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.name


class Center(TenantMixin, TimeStampedModel):
    class State(models.TextChoices):
        ACTIVE = "active", _("Faol")
        GRACE = "grace", _("Muhlatda")
        BLOCKED = "blocked", _("To'xtatilgan")

    name = models.CharField(_("nomi"), max_length=200)
    plan = models.ForeignKey(
        Plan,
        verbose_name=_("tarif"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="centers",
        help_text=_("Bo'sh bo'lsa — hamma bo'lim ochiq va cheklov yo'q."),
    )
    extra_features = _feature_list(_("qo'shimcha bo'limlar"))
    paid_until = models.DateField(
        _("to'langan muddat"), null=True, blank=True, help_text=_("Bo'sh — muddatsiz.")
    )
    is_suspended = models.BooleanField(_("qo'lda to'xtatilgan"), default=False)
    # Har kecha hisoblanadi (`tasks.refresh_usage`): panel va disk cheklovi shundan foydalanadi.
    students_count = models.PositiveIntegerField(_("o'quvchilar"), default=0, editable=False)
    staff_count = models.PositiveIntegerField(_("xodimlar"), default=0, editable=False)
    disk_bytes = models.PositiveBigIntegerField(_("disk"), default=0, editable=False)

    class Meta:
        verbose_name = _("markaz")
        verbose_name_plural = _("markazlar")

    def __str__(self) -> str:
        return self.name

    @property
    def features(self) -> frozenset[str]:
        """Ochiq bo'limlar: tarifdagilar va shu markazga alohida ochilganlar."""
        if self.plan is None:
            return frozenset(Feature.values)
        return with_dependencies({*self.plan.features, *self.extra_features})

    @property
    def state(self) -> str:
        if self.is_suspended:
            return self.State.BLOCKED
        if self.paid_until is None:
            return self.State.ACTIVE
        overdue = (timezone.localdate() - self.paid_until).days
        if overdue <= 0:
            return self.State.ACTIVE
        grace = self.plan.grace_days if self.plan else 0
        return self.State.GRACE if overdue <= grace else self.State.BLOCKED

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
