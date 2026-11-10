"""Markazlar: har markaz PostgreSQL'da alohida sxemada (django-tenants), bu jadvallar — `public`da.

Markaz manzil (domen) bo'yicha aniqlanadi. Sifat Edu — birinchi markaz.
"""

import uuid
from decimal import Decimal
from typing import Any

from auditlog.context import disable_auditlog
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
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
    trial_days = models.PositiveSmallIntegerField(_("bepul sinov, kun"), default=14)
    otp_sms_monthly = models.PositiveIntegerField(
        _("platforma hisobidan SMS kod, oyiga"),
        default=300,
        help_text=_("Markaz o'z Eskiz'ini ulamaguncha o'quvchilarning kirish kodlari uchun."),
    )
    ai_monthly_usd = models.DecimalField(
        _("AI oylik budjeti, $"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Bo'sh — cheklanmagan. Kalit platformaniki, xarajat ham."),
    )
    is_public = models.BooleanField(_("saytda ko'rinadi"), default=True)
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
    is_trial = models.BooleanField(
        _("bepul sinovda"), default=False, help_text=_("Faqat ogohlantirish matniga ta'sir qiladi.")
    )
    ai_monthly_usd = models.DecimalField(
        _("AI oylik budjeti, $"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Bo'sh — tarifdagi qiymat."),
    )
    owner_name = models.CharField(_("egasi"), max_length=301, blank=True)
    owner_phone = models.CharField(_("egasining telefoni"), max_length=13, blank=True)
    # Har kecha hisoblanadi (`tasks.refresh_usage`): panel va disk cheklovi shundan foydalanadi.
    students_count = models.PositiveIntegerField(_("o'quvchilar"), default=0, editable=False)
    staff_count = models.PositiveIntegerField(_("xodimlar"), default=0, editable=False)
    disk_bytes = models.PositiveBigIntegerField(_("disk"), default=0, editable=False)

    class Meta:
        verbose_name = _("markaz")
        verbose_name_plural = _("markazlar")
        constraints = [
            # Bepul sinovni qayta-qayta olib bo'lmasin.
            models.UniqueConstraint(
                fields=["owner_phone"], condition=~Q(owner_phone=""), name="center_owner_phone_uniq"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def ai_limit(self) -> Decimal | None:
        """AI uchun oylik chegara. `None` — tarif cheklamaydi."""
        if self.ai_monthly_usd is not None:
            return self.ai_monthly_usd
        return self.plan.ai_monthly_usd if self.plan else None

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


class Signup(TimeStampedModel):
    """Markaz egasining arizasi: telefon tasdiqlangach markaz fonda tayyorlanadi."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Kod kutilmoqda")
        PREPARING = "preparing", _("Tayyorlanmoqda")
        READY = "ready", _("Tayyor")
        FAILED = "failed", _("Xato")

    # Manzil va telefon shu holatlarda band.
    TAKEN = (Status.PREPARING, Status.READY)

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.PENDING
    )
    plan = models.ForeignKey(Plan, verbose_name=_("tarif"), on_delete=models.PROTECT)
    name = models.CharField(_("markaz nomi"), max_length=200)
    slug = models.CharField(_("manzil"), max_length=30)
    first_name = models.CharField(_("ism"), max_length=150)
    last_name = models.CharField(_("familiya"), max_length=150, blank=True)
    phone = models.CharField(_("telefon"), max_length=13, db_index=True)
    # Faqat parol xeshi va faqat markaz tayyor bo'lguncha.
    password_hash = models.CharField(max_length=128, blank=True, editable=False)
    locale = models.CharField(_("til"), max_length=2, default="uz")
    center = models.ForeignKey(
        Center, verbose_name=_("markaz"), on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = _("ariza")
        verbose_name_plural = _("arizalar")
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=Q(status__in=("preparing", "ready")),
                name="signup_slug_uniq",
            ),
            models.UniqueConstraint(
                fields=["phone"],
                condition=Q(status__in=("preparing", "ready")),
                name="signup_phone_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.slug} · {self.get_status_display()}"
