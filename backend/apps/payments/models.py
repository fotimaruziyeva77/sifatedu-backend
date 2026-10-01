"""Buyurtma, to'lov tranzaksiyasi, log va refund.

Summa har doim serverda hisoblanadi (`apps/payments/pricing.py`), kurs esa faqat to'lov
tizimining tasdig'idan keyin ochiladi.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

# To'lanmagan buyurtma shu muddatdan keyin `EXPIRED` bo'ladi.
ORDER_TTL_MINUTES = 30
# Offlayn to'lovda bir martada nechta oyni to'lash mumkin.
MAX_MONTHS = 12


class Provider(models.TextChoices):
    CLICK = "CLICK", "Click"


class Order(TimeStampedModel):
    """Bitta kursni sotib olish. Obuna va to'plam — 2-bosqich."""

    class Status(models.TextChoices):
        NEW = "NEW", _("To'lov kutilmoqda")
        PAID = "PAID", _("To'langan")
        EXPIRED = "EXPIRED", _("Muddati o'tgan")
        CANCELLED = "CANCELLED", _("Bekor qilingan")
        REFUNDED = "REFUNDED", _("Qaytarilgan")

    class Format(models.TextChoices):
        ONLINE = "ONLINE", _("Onlayn")
        OFFLINE = "OFFLINE", _("Offlayn")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("xaridor"),
        on_delete=models.PROTECT,
        related_name="orders",
    )
    course = models.ForeignKey(
        "catalog.Course",
        verbose_name=_("kurs"),
        on_delete=models.PROTECT,
        related_name="orders",
    )
    study_format = models.CharField(
        _("shakl"), max_length=10, choices=Format.choices, default=Format.ONLINE
    )
    months = models.PositiveSmallIntegerField(
        _("oylar"), default=1, help_text=_("Offlayn to'lov uchun: nechta oyga to'langan.")
    )
    amount = models.PositiveIntegerField(_("summa (so'm)"))
    # Chegirma: do'stning birinchi to'lovi (REFERRAL) yoki taklif qilganning kuponi (COUPON).
    full_amount = models.PositiveIntegerField(_("chegirmasiz summa"), null=True, blank=True)
    discount_percent = models.PositiveSmallIntegerField(_("chegirma (%)"), default=0)
    discount_reason = models.CharField(_("chegirma sababi"), max_length=10, blank=True)
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.NEW, db_index=True
    )
    provider = models.CharField(
        _("to'lov tizimi"), max_length=10, choices=Provider.choices, default=Provider.CLICK
    )
    paid_at = models.DateTimeField(_("to'langan vaqt"), null=True, blank=True)

    class Meta:
        verbose_name = _("buyurtma")
        verbose_name_plural = _("buyurtmalar")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"#{self.pk} — {self.course} ({self.amount:,} so'm)".replace(",", " ")

    @property
    def is_open(self) -> bool:
        """Hali to'lanishi mumkinmi."""
        return self.status == self.Status.NEW


class PaymentTransaction(TimeStampedModel):
    """To'lov tizimidagi bitta tranzaksiya.

    `provider_trans_id` unikal: Click bir so'rovni qayta yuborsa ham ikki marta
    qayta ishlanmaydi.
    """

    class Status(models.TextChoices):
        PREPARED = "PREPARED", _("Tayyorlangan")
        CONFIRMED = "CONFIRMED", _("Tasdiqlangan")
        CANCELLED = "CANCELLED", _("Bekor qilingan")

    order = models.ForeignKey(
        Order, verbose_name=_("buyurtma"), on_delete=models.PROTECT, related_name="transactions"
    )
    provider = models.CharField(
        _("to'lov tizimi"), max_length=10, choices=Provider.choices, default=Provider.CLICK
    )
    provider_trans_id = models.CharField(_("tranzaksiya raqami"), max_length=64)
    paydoc_id = models.CharField(_("to'lov hujjati"), max_length=64, blank=True)
    amount = models.PositiveIntegerField(_("summa (so'm)"))
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.PREPARED, db_index=True
    )
    fiscal_receipt_url = models.URLField(_("fiskal chek"), blank=True)
    confirmed_at = models.DateTimeField(_("tasdiqlangan vaqt"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("bekor qilingan vaqt"), null=True, blank=True)

    class Meta:
        verbose_name = _("to'lov tranzaksiyasi")
        verbose_name_plural = _("to'lov tranzaksiyalari")
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_trans_id"], name="unique_provider_transaction"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} {self.provider_trans_id}"


class PaymentLog(TimeStampedModel):
    """To'lov tizimi bilan bo'lgan har bir so'rov va javob (TZ talabi)."""

    provider = models.CharField(
        _("to'lov tizimi"), max_length=10, choices=Provider.choices, default=Provider.CLICK
    )
    action = models.CharField(_("amal"), max_length=40)
    order = models.ForeignKey(
        Order,
        verbose_name=_("buyurtma"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    request = models.JSONField(_("so'rov"), default=dict, blank=True)
    response = models.JSONField(_("javob"), default=dict, blank=True)
    ip = models.GenericIPAddressField(_("IP"), null=True, blank=True)

    class Meta:
        verbose_name = _("to'lov logi")
        verbose_name_plural = _("to'lov loglari")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["provider", "action", "created_at"])]

    def __str__(self) -> str:
        return f"{self.provider} {self.action} {self.created_at:%Y-%m-%d %H:%M}"


class Refund(TimeStampedModel):
    """Pulni qaytarish. 1-bosqichda pul Click kabinetida qo'lda qaytariladi."""

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", _("So'ralgan")
        APPROVED = "APPROVED", _("Tasdiqlangan")
        REJECTED = "REJECTED", _("Rad etilgan")
        DONE = "DONE", _("Pul qaytarilgan")

    order = models.ForeignKey(
        Order, verbose_name=_("buyurtma"), on_delete=models.PROTECT, related_name="refunds"
    )
    amount = models.PositiveIntegerField(_("summa (so'm)"))
    reason = models.TextField(_("sabab"), blank=True)
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.REQUESTED, db_index=True
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("kim qaror qilgan"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refund_decisions",
    )
    decided_at = models.DateTimeField(_("qaror vaqti"), null=True, blank=True)
    note = models.TextField(_("izoh"), blank=True)

    class Meta:
        verbose_name = _("pul qaytarish")
        verbose_name_plural = _("pul qaytarishlar")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"#{self.order_id} — {self.amount:,} so'm".replace(",", " ")
