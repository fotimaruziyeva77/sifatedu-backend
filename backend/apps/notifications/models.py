"""Xabarnomalar: kabinetdagi xabar (`Notification`) va admin yuboradigan xabar (`Broadcast`).

Har bir xabar avval kabinetga yoziladi (hammaga yetadi, bepul), keyin tashqi kanallarga:
Telegram — ulaganlarga, SMS — Telegram'i yo'qlarga va faqat SMS matni berilgan bo'lsa.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, URLValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.core.storage import public_storage

if TYPE_CHECKING:
    from apps.learning.models import StudyGroup


def validate_link(value: str) -> None:
    """Sayt ichidagi yo'l (`/dashboard/...`) yoki https havola (Meet, Zoom)."""
    if value.startswith("/") and not value.startswith("//"):
        return
    URLValidator(schemes=["https"], message=_("Havola https:// yoki / bilan boshlanishi kerak."))(
        value
    )


def broadcast_image_path(instance: "Broadcast", filename: str) -> str:
    return f"broadcasts/{uuid4().hex}{Path(filename).suffix.lower() or '.jpg'}"


class Delivery(models.TextChoices):
    """Tashqi kanal holati. Bo'sh qiymat — bu kanal ishlatilmaydi."""

    QUEUED = "QUEUED", _("Navbatda")
    SENT = "SENT", _("Yuborildi")
    FAILED = "FAILED", _("Yetmadi")


class Broadcast(TimeStampedModel):
    """Admin yoki menejer yozgan xabar: filtrlar bo'yicha tanlangan o'quvchilarga boradi."""

    class Kind(models.TextChoices):
        INFO = "INFO", _("O'quv xabari")
        PROMO = "PROMO", _("Aksiya va yangilik")

    class Audience(models.TextChoices):
        ALL = "ALL", _("Hamma")
        ADULT = "ADULT", _("Kattalar")
        KIDS = "KIDS", _("SIFAT Kids")

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Qoralama")
        SCHEDULED = "SCHEDULED", _("Navbatda")
        SENT = "SENT", _("Yuborildi")

    title = models.CharField(_("sarlavha"), max_length=120)
    body = models.TextField(_("matn"), max_length=2000)
    link = models.CharField(
        _("havola"),
        max_length=500,
        blank=True,
        validators=[validate_link],
        help_text=_(
            "Ixtiyoriy: https://meet.google.com/... yoki sayt ichidagi yo'l, "
            "masalan /dashboard/courses"
        ),
    )
    image = models.ImageField(
        _("rasm"),
        storage=public_storage,
        upload_to=broadcast_image_path,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        help_text=_("Ixtiyoriy: Telegram'da xabar bilan birga ketadi (JPG yoki PNG)."),
    )
    kind = models.CharField(
        _("turi"),
        max_length=10,
        choices=Kind.choices,
        default=Kind.INFO,
        help_text=_(
            "Aksiya Telegram va SMS orqali faqat rozilik berganlarga boradi, "
            "kechasi (22:00–09:00) esa ertalab 09:00 ga suriladi."
        ),
    )
    audience = models.CharField(
        _("kabinet"), max_length=10, choices=Audience.choices, default=Audience.ALL
    )
    courses = models.ManyToManyField(
        "catalog.Course",
        verbose_name=_("kurslar"),
        blank=True,
        related_name="+",
        help_text=_("Tanlansa — faqat shu kurslarga yozilgan o'quvchilar."),
    )
    groups: "models.ManyToManyField[StudyGroup, Any]" = models.ManyToManyField(
        "learning.StudyGroup",
        verbose_name=_("guruhlar"),
        blank=True,
        related_name="+",
        help_text=_("Tanlansa — faqat shu guruhlar o'quvchilari."),
    )
    without_course = models.BooleanField(
        _("faqat kurs tanlamaganlar"),
        default=False,
        help_text=_("Birorta kursga yozilmagan o'quvchilar (masalan, ro'yxatdan o'tib ketganlar)."),
    )
    joined_from = models.DateField(_("ro'yxatdan o'tgan: dan"), null=True, blank=True)
    joined_to = models.DateField(_("ro'yxatdan o'tgan: gacha"), null=True, blank=True)
    send_telegram = models.BooleanField(
        _("Telegram"), default=True, help_text=_("Telegram'ini ulagan o'quvchilarga.")
    )
    bot_all = models.BooleanField(
        _("botdagi hammaga ham"),
        default=False,
        help_text=_(
            "Botga /start bosgan hamma (ro'yxatdan o'tmaganlar ham) Telegram'da oladi. Faqat "
            "filtrsiz xabarda; kechasi (22:00–09:00) yozilgani ertalab 09:00 da ketadi."
        ),
    )
    send_sms = models.BooleanField(
        _("SMS"),
        default=False,
        help_text=_(
            "Telegram'i yo'qlarga SMS. Pullik; matn Eskiz'da tasdiqlangan shablonga mos "
            "bo'lishi kerak, aks holda Eskiz uni yubormaydi."
        ),
    )
    sms_text = models.CharField(_("SMS matni"), max_length=300, blank=True)
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("muallif"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    scheduled_for = models.DateTimeField(_("yuborish vaqti"), null=True, blank=True)
    sent_at = models.DateTimeField(_("yuborilgan"), null=True, blank=True)
    recipients = models.PositiveIntegerField(_("qabul qiluvchilar"), default=0)
    # "Botdagi hammaga": ro'yxatdan o'tmagan (yoki Telegram'i ulanmagan) bot foydalanuvchilari.
    bot_recipients = models.PositiveIntegerField(_("bot orqali"), default=0)
    bot_sent = models.PositiveIntegerField(_("botda yetdi"), default=0)
    bot_failed = models.PositiveIntegerField(_("botda yetmadi"), default=0)

    class Meta:
        verbose_name = _("xabar")
        verbose_name_plural = _("xabar yuborish")
        ordering = ("-created_at",)
        permissions = [("send_broadcast", _("Xabarni yuborish"))]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        errors = {}
        if self.send_sms and not self.sms_text.strip():
            errors["sms_text"] = _("SMS yuborilsa, SMS matnini yozing.")
        if not self.send_sms and self.sms_text.strip():
            errors["send_sms"] = _(
                "SMS matni yozilgan: SMS'ni ham belgilang yoki matnni o'chiring."
            )
        if self.joined_from and self.joined_to and self.joined_from > self.joined_to:
            errors["joined_to"] = _("Oxirgi sana boshlanish sanasidan oldin bo'lmasin.")
        if errors:
            raise ValidationError(errors)

    @property
    def is_draft(self) -> bool:
        return self.status == self.Status.DRAFT


class Notification(models.Model):
    """Foydalanuvchining kabinetidagi xabar va uning Telegram/SMS orqali yetkazilishi."""

    class Kind(models.TextChoices):
        BROADCAST = "BROADCAST", _("Xabar")
        PAYMENT = "PAYMENT", _("To'lov")
        COURSE_OPENED = "COURSE_OPENED", _("Kurs ochildi")
        ACCESS_EXPIRING = "ACCESS_EXPIRING", _("Muddat tugayapti")
        ACCESS_EXPIRED = "ACCESS_EXPIRED", _("Muddat tugadi")
        HOMEWORK_SUBMITTED = "HOMEWORK_SUBMITTED", _("Yangi uy vazifasi javobi")
        HOMEWORK_REVIEWED = "HOMEWORK_REVIEWED", _("Uy vazifasi tekshirildi")
        INACTIVE = "INACTIVE", _("O'qishga qaytish eslatmasi")
        LIVE_REMINDER = "LIVE_REMINDER", _("Jonli dars eslatmasi")
        LIVE_CANCELED = "LIVE_CANCELED", _("Dars bekor qilindi")
        LIVE_ABSENT = "LIVE_ABSENT", _("Darsda bo'lmadi")
        LIVE_RECORDING = "LIVE_RECORDING", _("Dars yozuvi")
        LESSON_OPENED = "LESSON_OPENED", _("Yangi dars ochildi")
        EXAM_DRAFT = "EXAM_DRAFT", _("Imtihonni tayyorlash")
        EXAM_OPENED = "EXAM_OPENED", _("Imtihon ochildi")
        EXAM_RESULT = "EXAM_RESULT", _("Imtihon natijasi")
        CERTIFICATE = "CERTIFICATE", _("Sertifikat")
        REWARD = "REWARD", _("Mukofot")
        SHOP = "SHOP", _("Do'kon")
        COUPON = "COUPON", _("Chegirma kuponi")
        DAILY_TEST = "DAILY_TEST", _("Kunlik test")
        DAILY_TEST_TEACHER = "DAILY_TEST_TEACHER", _("Kunlik test: o'qituvchiga")
        TEST = "TEST", _("Sinov")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("foydalanuvchi"),
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(_("turi"), max_length=20, choices=Kind.choices)
    broadcast = models.ForeignKey(
        Broadcast,
        verbose_name=_("xabar"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    title = models.CharField(_("sarlavha"), max_length=120)
    body = models.TextField(_("matn"), blank=True)
    link = models.CharField(_("havola"), max_length=500, blank=True)
    created_at = models.DateTimeField(_("vaqt"), auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(_("o'qilgan"), null=True, blank=True)
    telegram = models.CharField(_("Telegram"), max_length=10, choices=Delivery.choices, blank=True)
    sms = models.CharField(_("SMS"), max_length=10, choices=Delivery.choices, blank=True)
    # Telegram yetmasa, SMS shu matn bilan ketadi. Bo'sh — SMS yuborilmaydi.
    sms_text = models.CharField(_("SMS matni"), max_length=300, blank=True)
    # Telegram'da xabar bilan birga: rasm (ochiq storage'dagi fayl) va botda test tugmasi.
    image = models.CharField(_("rasm"), max_length=200, blank=True, editable=False)
    quiz = models.ForeignKey(
        "quizzes.Quiz",
        verbose_name=_("test"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text=_('Telegram\'da "Testni boshlash" tugmasi — test botda ochiladi.'),
    )
    error = models.CharField(_("yetkazish xatosi"), max_length=300, blank=True)
    # Avtomatik xabarlar bir marta yuborilishi uchun (masalan, `expiring:12:2026-10-05`).
    dedupe_key = models.CharField(
        max_length=120, null=True, blank=True, unique=True, editable=False
    )

    class Meta:
        verbose_name = _("yuborilgan xabar")
        verbose_name_plural = _("yuborilgan xabarlar")
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=["user", "read_at"])]
        constraints = [
            models.UniqueConstraint(fields=["broadcast", "user"], name="unique_broadcast_recipient")
        ]

    def __str__(self) -> str:
        return self.title
