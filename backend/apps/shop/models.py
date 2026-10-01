"""Coin do'koni: sovg'alar va o'quvchilarning buyurtmalari.

Narx — coin (`apps.rewards` hamyonidan yechiladi). Zaxira bo'sh — cheksiz. Buyurtma holati:
yangi → tayyor → topshirildi, yoki bekor (coin qaytadi, zaxira tiklanadi).
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.core.storage import public_storage


class Product(TimeStampedModel):
    class Kind(models.TextChoices):
        DIGITAL = "DIGITAL", _("Raqamli")
        PHYSICAL = "PHYSICAL", _("Jismoniy")

    class Audience(models.TextChoices):
        ALL = "ALL", _("Hammaga")
        ADULT = "ADULT", _("Kattalarga")
        KIDS = "KIDS", _("SIFAT Kids")

    name = models.CharField(_("nomi"), max_length=120)
    description = models.TextField(_("tavsif"), blank=True)
    image = models.ImageField(_("rasm"), storage=public_storage, upload_to="shop/", blank=True)
    price = models.PositiveIntegerField(_("narx (coin)"), validators=[MinValueValidator(1)])
    kind = models.CharField(_("turi"), max_length=10, choices=Kind.choices, default=Kind.PHYSICAL)
    stock = models.PositiveIntegerField(
        _("zaxira"), null=True, blank=True, help_text=_("Bo'sh — cheksiz.")
    )
    audience = models.CharField(
        _("kimga"), max_length=10, choices=Audience.choices, default=Audience.ALL
    )
    is_active = models.BooleanField(_("sotuvda"), default=True)
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("sovg'a")
        verbose_name_plural = _("sovg'alar")
        ordering = ("order", "price", "pk")

    def __str__(self) -> str:
        return f"{self.name} · {self.price} coin"

    @property
    def in_stock(self) -> bool:
        return self.stock is None or self.stock > 0


class Purchase(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "NEW", _("Yangi")
        READY = "READY", _("Tayyor")
        DELIVERED = "DELIVERED", _("Topshirildi")
        CANCELED = "CANCELED", _("Bekor qilindi")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.PROTECT,
        related_name="purchases",
    )
    product = models.ForeignKey(
        Product, verbose_name=_("sovg'a"), on_delete=models.PROTECT, related_name="purchases"
    )
    # Olingan paytdagi nom va narx: keyin o'zgarsa ham buyurtmada o'sha qoladi.
    name = models.CharField(_("nomi"), max_length=120)
    price = models.PositiveIntegerField(_("narx (coin)"))
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.NEW, db_index=True
    )
    note = models.CharField(
        _("izoh o'quvchiga"),
        max_length=300,
        blank=True,
        help_text=_("Masalan: qayerdan va qachon olish mumkin."),
    )
    ready_at = models.DateTimeField(_("tayyor bo'ldi"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("topshirildi"), null=True, blank=True)
    canceled_at = models.DateTimeField(_("bekor qilindi"), null=True, blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("kim"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = _("buyurtma")
        verbose_name_plural = _("do'kon buyurtmalari")
        ordering = ("-created_at", "-pk")

    def __str__(self) -> str:
        return f"{self.user} · {self.name}"

    @property
    def is_open(self) -> bool:
        return self.status in (self.Status.NEW, self.Status.READY)
