from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Course
from apps.core.models import TimeStampedModel
from apps.users.models import phone_validator


class Lead(TimeStampedModel):
    """Landing'dan qoldirilgan ariza (TZ 4.1)."""

    class Status(models.TextChoices):
        NEW = "NEW", _("Yangi")
        CONTACTED = "CONTACTED", _("Bog'lanildi")
        CONVERTED = "CONVERTED", _("Mijozga aylandi")
        REJECTED = "REJECTED", _("Rad etildi")

    class Source(models.TextChoices):
        FORM = "FORM", _("Sayt formasi")
        AI_WEB = "AI_WEB", _("AI chat (sayt)")
        AI_TELEGRAM = "AI_TELEGRAM", _("AI chat (Telegram)")
        BOT_TEST = "BOT_TEST", _("Botdagi daraja testi")

    name = models.CharField(_("ism"), max_length=100)
    phone = models.CharField(
        _("telefon"), max_length=13, validators=[phone_validator], db_index=True
    )
    course = models.ForeignKey(
        Course,
        verbose_name=_("qiziqqan kurs"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    comment = models.TextField(_("izoh"), blank=True)
    status = models.CharField(
        _("holat"), max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    manager_note = models.TextField(_("menejer izohi"), blank=True)
    source = models.CharField(
        _("manba"), max_length=12, choices=Source.choices, default=Source.FORM, db_index=True
    )
    submissions = models.PositiveSmallIntegerField(
        _("murojaatlar soni"),
        default=1,
        help_text=_("Bitta raqamdan 24 soat ichida kelgan takroriy arizalar shu yerga qo'shiladi."),
    )

    locale = models.CharField(_("til"), max_length=2, choices=settings.LANGUAGES, default="uz")
    source_page = models.CharField(_("manba sahifa"), max_length=500, blank=True)
    utm_source = models.CharField("utm_source", max_length=200, blank=True)
    utm_medium = models.CharField("utm_medium", max_length=200, blank=True)
    utm_campaign = models.CharField("utm_campaign", max_length=200, blank=True)
    utm_term = models.CharField("utm_term", max_length=200, blank=True)
    utm_content = models.CharField("utm_content", max_length=200, blank=True)
    ip = models.GenericIPAddressField(_("IP"), null=True, blank=True)
    user_agent = models.CharField(_("brauzer"), max_length=500, blank=True)
    telegram_sent_at = models.DateTimeField(_("Telegram'ga yuborilgan"), null=True, blank=True)

    class Meta:
        verbose_name = _("ariza")
        verbose_name_plural = _("arizalar")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"
