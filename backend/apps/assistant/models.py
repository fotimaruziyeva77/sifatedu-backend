"""AI sotuv maslahatchisi: sozlamalar, suhbatlar va xabarlar."""

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.leads.models import Lead


class AssistantSettings(models.Model):
    """Yagona yozuv (pk=1): AI'ni yoqish, budjet va agent bilishi kerak bo'lgan faktlar."""

    enabled = models.BooleanField(
        _("saytda yoqilgan"),
        default=True,
        help_text=_(
            "O'chirilsa, saytdagi chat yashiriladi. Telegram bot esa faqat raqam so'rab, ariza "
            "qabul qiladi."
        ),
    )
    knowledge = models.TextField(
        _("qo'shimcha ma'lumot"),
        blank=True,
        help_text=_(
            "AI bilishi kerak bo'lgan faktlar: chegirmalar, bo'lib to'lash, sertifikat, sinov "
            "darsi, guruhlar jadvali, mo'ljal. AI faqat shu yerda va saytda yozilgan narsani "
            "aytadi."
        ),
    )
    daily_budget_usd = models.DecimalField(
        _("kunlik budjet ($)"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("5"),
        help_text=_(
            "Tugasa, AI o'rniga oddiy rejim ishlaydi: raqam so'raydi. 0 — AI to'xtatilgan."
        ),
    )
    monthly_budget_usd = models.DecimalField(
        _("oylik budjet ($)"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("100"),
        help_text=_("80 foiziga yetganda Telegram'ga ogohlantirish keladi."),
    )
    max_user_messages = models.PositiveSmallIntegerField(
        _("bitta suhbatdagi xabarlar"),
        default=30,
        help_text=_("Undan keyin AI javob bermaydi va raqam qoldirishni so'raydi."),
    )
    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    class Meta:
        verbose_name = _("AI sozlamalari")
        verbose_name_plural = _("AI sozlamalari")

    def __str__(self) -> str:
        return str(_("AI sozlamalari"))

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "AssistantSettings":
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class Conversation(TimeStampedModel):
    """Bitta mijoz bilan suhbat: saytda cookie orqali, Telegram'da chat ID orqali topiladi."""

    class Channel(models.TextChoices):
        WEB = "WEB", _("Sayt")
        TELEGRAM = "TELEGRAM", _("Telegram")

    class Status(models.TextChoices):
        OPEN = "OPEN", _("Ochiq")
        MANAGER = "MANAGER", _("Menejer kerak")
        CLOSED = "CLOSED", _("Yopilgan")

    channel = models.CharField(
        _("kanal"), max_length=10, choices=Channel.choices, default=Channel.WEB, db_index=True
    )
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    # Saytda: cookie'dagi tasodifiy kalitning SHA-256 xeshi (kalitning o'zi saqlanmaydi).
    token_hash = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("foydalanuvchi"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_conversations",
    )
    telegram_chat_id = models.BigIntegerField(
        _("Telegram chat"), null=True, blank=True, db_index=True
    )
    telegram_username = models.CharField(_("Telegram username"), max_length=64, blank=True)
    name = models.CharField(_("ism"), max_length=100, blank=True)
    lead = models.ForeignKey(
        Lead,
        verbose_name=_("ariza"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    locale = models.CharField(_("til"), max_length=2, choices=settings.LANGUAGES, default="uz")
    source_page = models.CharField(_("boshlangan sahifa"), max_length=500, blank=True)
    context = models.JSONField(_("kontekst"), default=dict, blank=True)
    # Belgi → haqiqiy raqam: {"1": "+998901234567"}. AI faqat belgini ko'radi (phones.py).
    phones = models.JSONField(default=dict, blank=True, editable=False)
    summary = models.TextField(_("menejer uchun xulosa"), blank=True)
    user_messages = models.PositiveSmallIntegerField(_("mijoz xabarlari"), default=0)
    cost_usd = models.DecimalField(_("xarajat ($)"), max_digits=10, decimal_places=6, default=0)
    last_message_at = models.DateTimeField(_("oxirgi xabar"), null=True, blank=True, db_index=True)
    # Javob tayyorlanayotgan bo'lsa — qachondan beri (bir vaqtda ikkita javob bo'lmasin).
    pending_since = models.DateTimeField(null=True, blank=True, editable=False)
    ip_hash = models.CharField(max_length=64, blank=True, editable=False)
    anonymized_at = models.DateTimeField(_("anonimlashtirilgan"), null=True, blank=True)

    class Meta:
        verbose_name = _("suhbat")
        verbose_name_plural = _("suhbatlar")
        ordering = ("-last_message_at", "-id")

    def __str__(self) -> str:
        who = self.name or self.telegram_username or self.get_channel_display()
        return f"#{self.pk} · {who}"


class Message(models.Model):
    """Suhbatdagi xabar. `content` — modelga aynan qanday yuborilgan bo'lsa (raqamlar belgi
    bilan, Gemini imzolari bilan); `text` — mijoz va admin ko'radigan matn."""

    class Role(models.TextChoices):
        USER = "USER", _("Mijoz")
        ASSISTANT = "ASSISTANT", _("AI")
        TOOL = "TOOL", _("Vosita natijasi")

    class Rating(models.IntegerChoices):
        GOOD = 1, "👍"
        BAD = -1, "👎"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages", verbose_name=_("suhbat")
    )
    role = models.CharField(_("kim"), max_length=10, choices=Role.choices)
    text = models.TextField(_("matn"), blank=True)
    content = models.JSONField(default=list)
    attachments = models.JSONField(_("kurs kartochkalari"), default=list, blank=True)
    model = models.CharField(_("model"), max_length=60, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    cache_write_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(_("narx ($)"), max_digits=10, decimal_places=6, default=0)
    latency_ms = models.PositiveIntegerField(_("javob vaqti (ms)"), null=True, blank=True)
    rating = models.SmallIntegerField(_("baho"), choices=Rating.choices, null=True, blank=True)
    created_at = models.DateTimeField(_("vaqt"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("xabar")
        verbose_name_plural = _("xabarlar")
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.get_role_display()}: {self.text[:60]}"
