"""Telegram bot: botdagi odamlar (ro'yxatdan o'tmaganlar ham) va majburiy obuna kanallari.

Bot akkauntni `SocialAccount` (Telegram) orqali taniydi — sayt bilan bitta manba. `BotChat`da
faqat botning o'z sozlamalari: til, yangiliklar, test holati.
"""

from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class BotChat(TimeStampedModel):
    """Botga /start bosgan odam. Yangiliklar ro'yxatdan o'tmaganlarga ham shu ro'yxat bo'yicha."""

    chat_id = models.BigIntegerField(_("Telegram ID"), unique=True)
    first_name = models.CharField(_("ism"), max_length=150, blank=True)
    username = models.CharField(_("username"), max_length=64, blank=True)
    language = models.CharField(_("til"), max_length=2, choices=settings.LANGUAGES, blank=True)
    news = models.BooleanField(
        _("yangiliklar"), default=True, help_text=_("O'chirilsa, admin xabarlari botda kelmaydi.")
    )
    blocked_at = models.DateTimeField(_("botni bloklagan"), null=True, blank=True)
    # Kontakt orqali Telegram tasdiqlagan raqam. Botdan saytga parolsiz kirish faqat shu raqam
    # akkauntnikiga teng bo'lsa: saytdagi havola bilan ulangan (masalan, umumiy kompyuterdagi
    # birovning) Telegram akkauntga kira olmasin.
    verified_phone = models.CharField(_("tasdiqlangan telefon"), max_length=13, blank=True)
    # /start r_<kod>: ro'yxatdan o'tganda "kim taklif qildi" shu koddan yoziladi.
    referral_code = models.CharField(_("taklif kodi"), max_length=16, blank=True)
    # Test jarayoni va kutilayotgan javob: {"quiz": {...}, "await": "text", "start": "..."}.
    state: "models.JSONField[dict[str, Any], dict[str, Any]]" = models.JSONField(
        default=dict, blank=True, editable=False
    )
    last_seen_at = models.DateTimeField(_("oxirgi faollik"), null=True, blank=True)

    class Meta:
        verbose_name = _("bot foydalanuvchisi")
        verbose_name_plural = _("bot foydalanuvchilari")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        name = self.first_name or str(self.chat_id)
        return f"{name} (@{self.username})" if self.username else name


class RequiredChannel(models.Model):
    """Botdan foydalanish uchun obuna bo'lish kerak bo'lgan kanal (faqat botda, saytda emas)."""

    title = models.CharField(_("nomi"), max_length=100)
    chat = models.CharField(
        _("kanal"),
        max_length=100,
        help_text=_(
            "@kanal_nomi yoki yopiq kanal ID si (-100…). Bot kanalda administrator bo'lsin."
        ),
    )
    url = models.URLField(_("havola"), help_text=_("https://t.me/kanal_nomi yoki taklif havolasi"))
    is_active = models.BooleanField(_("faol"), default=True)
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("majburiy kanal")
        verbose_name_plural = _("majburiy kanallar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title
