"""SMM agent: haftalik reja, tayyorlangan postlar va ularning holati (docs/smm-agent.md)."""

from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class SmmSettings(models.Model):
    """Markazda bitta qator. O'chiq turganda agent hech narsa qilmaydi."""

    enabled = models.BooleanField(
        _("yoqilgan"),
        default=False,
        help_text=_(
            "Yoqilsa, har yakshanba keyingi hafta rejasi tuziladi va postlar tayyorlanadi."
        ),
    )
    auto_publish = models.BooleanField(
        _("tasdiqsiz chiqarish"),
        default=False,
        help_text=_("O'chiq bo'lsa (tavsiya), har post avval Telegram'da tasdiqlanadi."),
    )
    channel = models.CharField(
        _("Telegram kanal"),
        max_length=100,
        blank=True,
        help_text=_("@sifatedu yoki -100… ID. Markaz boti kanalda administrator bo'lishi kerak."),
    )
    publish_hour = models.PositiveSmallIntegerField(
        _("chiqish soati"), default=19, help_text=_("Toshkent vaqti, 0–23.")
    )
    about = models.TextField(
        _("markaz haqida faktlar"),
        blank=True,
        help_text=_(
            "Agent faqat shu yerdagi va kurslar ro'yxatidagi faktlardan foydalanadi: natijalar, "
            "yangiliklar, chegirmalar, manzil. Har qatorda bitta fakt."
        ),
    )
    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    class Meta:
        verbose_name = _("SMM sozlamalari")
        verbose_name_plural = _("SMM sozlamalari")

    def __str__(self) -> str:
        return str(_("SMM sozlamalari"))

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SmmSettings":
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class Post(models.Model):
    class Kind(models.TextChoices):
        POST = "post", _("rasm")
        CAROUSEL = "carousel", _("karusel")
        SCRIPT = "script", _("suratga olish ssenariysi")

    class Formula(models.TextChoices):
        FAMILY = "family", _("oilaviy mini-sahna")
        RESULT = "result", _("haqiqiy natija")
        QUESTION = "question", _("ota-onaga savol")
        INSIDE = "inside", _("hech kim ko'rmagan joy")
        TIPS = "tips", _("foydali maslahat")
        HUMOR = "humor", _("IT hazili")
        STORY = "story", _("motivatsion hikoya")

    class Status(models.TextChoices):
        PLANNED = "planned", _("rejada")
        MAKING = "making", _("tayyorlanmoqda")
        REVIEW = "review", _("tasdiq kutmoqda")
        APPROVED = "approved", _("tasdiqlandi")
        PUBLISHING = "publishing", _("chiqarilmoqda")
        PUBLISHED = "published", _("chiqdi")
        REJECTED = "rejected", _("bekor qilindi")
        FAILED = "failed", _("xato")

    kind = models.CharField(_("turi"), max_length=10, choices=Kind.choices)
    formula = models.CharField(_("formula"), max_length=10, choices=Formula.choices)
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.PLANNED, db_index=True
    )
    publish_at = models.DateTimeField(_("chiqish vaqti"), db_index=True)
    topic = models.CharField(_("mavzu"), max_length=300)
    angle = models.TextField(_("g'oya"), blank=True)
    content = models.JSONField(_("mazmun"), default=dict, blank=True)
    caption = models.TextField(_("Instagram matni"), blank=True)
    caption_tg = models.TextField(_("Telegram matni"), blank=True)
    images = models.JSONField(_("rasmlar"), default=list, blank=True)
    # Tasdiqlovchilarga yuborilgan xabarlar: qaror qabul qilingach tugmalar olib tashlanadi.
    review_messages = models.JSONField(default=list, blank=True)
    channel_messages = models.JSONField(default=list, blank=True)
    attempts = models.PositiveSmallIntegerField(_("urinishlar"), default=0)
    cost_usd = models.DecimalField(_("AI xarajati ($)"), max_digits=8, decimal_places=4, default=0)
    error = models.TextField(_("xato"), blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("qaror qildi"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    published_at = models.DateTimeField(_("chiqqan vaqti"), null=True, blank=True)
    created_at = models.DateTimeField(_("yaratilgan"), auto_now_add=True)
    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    class Meta:
        verbose_name = _("SMM post")
        verbose_name_plural = _("SMM postlar")
        ordering = ["-publish_at"]

    def __str__(self) -> str:
        return self.topic

    @property
    def publishable(self) -> bool:
        """Ssenariy kanalga chiqmaydi: u markaz suratga olishi uchun."""
        return self.kind != self.Kind.SCRIPT
