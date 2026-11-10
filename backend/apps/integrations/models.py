"""Markazning o'z xizmatlari: Telegram bot, Click va Eskiz. Har markaz sxemasida bitta qator."""

from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _

from .fields import SecretField


class Integrations(models.Model):
    telegram_token = SecretField(_("bot tokeni"), blank=True, default="")
    telegram_username = models.CharField(_("bot nomi"), max_length=64, blank=True)
    telegram_webhook_secret = SecretField(_("webhook siri"), blank=True, default="")
    telegram_leads_chat_id = models.CharField(_("arizalar guruhi"), max_length=32, blank=True)
    telegram_reports_chat_id = models.CharField(_("hisobot guruhi"), max_length=32, blank=True)
    telegram_login = models.BooleanField(
        _("saytda Telegram orqali kirish"),
        default=False,
        help_text=_("BotFather'da /setdomain qilingandan keyin yoqiladi."),
    )

    click_service_id = models.CharField(_("Click service ID"), max_length=32, blank=True)
    click_merchant_id = models.CharField(_("Click merchant ID"), max_length=32, blank=True)
    click_merchant_user_id = models.CharField(_("Click user ID"), max_length=32, blank=True)
    click_secret_key = SecretField(_("Click maxfiy kaliti"), blank=True, default="")
    click_tin = models.CharField(_("STIR"), max_length=20, blank=True)

    eskiz_email = models.CharField(_("Eskiz email"), max_length=254, blank=True)
    eskiz_password = SecretField(_("Eskiz paroli"), blank=True, default="")
    eskiz_from = models.CharField(_("SMS jo'natuvchi"), max_length=20, blank=True)
    # Eskiz shablonidagi nom: markaz keyin nomini o'zgartirsa ham tasdiqlangan matn buzilmasin.
    eskiz_brand = models.CharField(_("SMS'dagi nom"), max_length=200, blank=True)

    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    class Meta:
        verbose_name = _("markaz kalitlari")
        verbose_name_plural = _("markaz kalitlari")

    def __str__(self) -> str:
        return str(_("Markaz kalitlari"))

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "Integrations":
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj
