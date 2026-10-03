from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.storage import public_storage

phone_validator = RegexValidator(
    regex=r"^\+998\d{9}$",
    message=_("Telefon raqami +998XXXXXXXXX formatida bo'lishi kerak."),
)


def avatar_path(instance: "User", filename: str) -> str:
    """Tasodifiy nom: URL'dan telefon yoki ismni bilib bo'lmaydi."""
    suffix = Path(filename).suffix.lower() or ".jpg"
    return f"avatars/{uuid4().hex}{suffix}"


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create_user(self, phone: str, password: str | None, **extra: Any) -> "User":
        if not phone:
            raise ValueError("Telefon raqami majburiy.")
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone: str, password: str | None = None, **extra: Any) -> "User":
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra)

    def create_superuser(self, phone: str, password: str | None = None, **extra: Any) -> "User":
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self._create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Audience(models.TextChoices):
        ADULT = "ADULT", _("15 yoshdan katta")
        KIDS = "KIDS", _("Bolalar (7–11 yosh)")

    phone = models.CharField(_("telefon"), max_length=13, unique=True, validators=[phone_validator])
    first_name = models.CharField(_("ism"), max_length=150, blank=True)
    last_name = models.CharField(_("familiya"), max_length=150, blank=True)
    locale = models.CharField(
        _("interfeys tili"), max_length=2, choices=settings.LANGUAGES, default="uz"
    )
    avatar = models.ImageField(_("rasm"), storage=public_storage, upload_to=avatar_path, blank=True)
    # Kabinet ko'rinishi shu qiymatga bog'liq: bolalar uchun alohida, kreativ kabinet.
    audience = models.CharField(
        _("kabinet ko'rinishi"),
        max_length=10,
        choices=Audience.choices,
        default=Audience.ADULT,
    )
    terms_accepted_at = models.DateTimeField(
        _("oferta va maxfiylik siyosati qabul qilingan"), null=True, blank=True
    )
    terms_version = models.CharField(
        _("qabul qilingan versiyalar"),
        max_length=80,
        blank=True,
        help_text=_("Masalan: offer:1.0, privacy:1.0"),
    )
    # Reklama qonuni va TZ 4.12: aksiyalar Telegram va SMS orqali faqat rozilik bilan yuboriladi.
    marketing_consent_at = models.DateTimeField(
        _("aksiya va yangiliklarga rozilik"),
        null=True,
        blank=True,
        help_text=_(
            "Bo'sh bo'lsa, aksiyalar Telegram va SMS orqali yuborilmaydi (kabinetda ko'rinadi)."
        ),
    )
    # Do'stni taklif qilish: shaxsiy kod (havolada) va kim taklif qilgani (ro'yxatdan o'tishda).
    referral_code = models.CharField(
        _("taklif kodi"), max_length=12, unique=True, null=True, blank=True, editable=False
    )
    # Reklama manbasi (bot havolasi `?start=ig` va h.k.): qaysi kanal o'quvchi olib kelyapti.
    signup_source = models.CharField(_("manba"), max_length=32, blank=True, db_index=True)
    referred_by = models.ForeignKey(
        "self",
        verbose_name=_("taklif qilgan"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )
    is_active = models.BooleanField(
        _("faol"),
        default=True,
        help_text=_("Foydalanuvchini bloklash uchun belgini olib tashlang."),
    )
    is_staff = models.BooleanField(
        _("xodim"), default=False, help_text=_("Admin panelga kira oladi.")
    )
    # Indeks: kunlik statistika shu maydon bo'yicha sanaydi.
    date_joined = models.DateTimeField(
        _("ro'yxatdan o'tgan sana"), default=timezone.now, db_index=True
    )

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        verbose_name = _("foydalanuvchi")
        verbose_name_plural = _("foydalanuvchilar")
        ordering = ("-date_joined",)

    def __str__(self) -> str:
        return self.get_full_name() or self.phone

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        return self.first_name or self.phone


class OneTimeCode(models.Model):
    """SMS orqali yuborilgan bir martalik kod. Kodning o'zi saqlanmaydi — faqat HMAC xeshi."""

    class Purpose(models.TextChoices):
        REGISTER = "register", _("Ro'yxatdan o'tish")
        RESET = "reset", _("Parolni tiklash")
        LINK = "link", _("Google yoki Telegram'ni bog'lash")

    phone = models.CharField(_("telefon"), max_length=13, db_index=True)
    purpose = models.CharField(_("maqsad"), max_length=10, choices=Purpose.choices)
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(_("urinishlar"), default=0)
    created_at = models.DateTimeField(_("yuborilgan"), auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(_("amal qiladi"))
    used_at = models.DateTimeField(_("yopilgan"), null=True, blank=True)
    ip = models.GenericIPAddressField(_("IP"), null=True, blank=True)

    class Meta:
        verbose_name = _("SMS kod")
        verbose_name_plural = _("SMS kodlar")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["phone", "purpose", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.phone} · {self.get_purpose_display()}"


class SocialAccount(models.Model):
    """Google yoki Telegram akkaunti. Parol saqlanmaydi — egalikni provayder tasdiqlaydi."""

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        TELEGRAM = "telegram", "Telegram"

    user = models.ForeignKey(
        "users.User",
        verbose_name=_("foydalanuvchi"),
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(_("provayder"), max_length=20, choices=Provider.choices)
    uid = models.CharField(_("provayderdagi id"), max_length=64)
    email = models.EmailField(_("email"), blank=True)
    created_at = models.DateTimeField(_("bog'langan"), auto_now_add=True)
    last_login_at = models.DateTimeField(_("oxirgi kirish"), null=True, blank=True)
    # Faqat Telegram: bot shu odamga xabar yozadimi. `notify` — foydalanuvchi tanlovi (sozlamalar),
    # `blocked_at` — Telegram "yozib bo'lmaydi" degan vaqt; botga qayta yozsa tozalanadi.
    notify = models.BooleanField(_("xabarlar yuborilsin"), default=True)
    blocked_at = models.DateTimeField(_("bot bloklangan"), null=True, blank=True)

    class Meta:
        verbose_name = _("ijtimoiy akkaunt")
        verbose_name_plural = _("ijtimoiy akkauntlar")
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=["provider", "uid"], name="unique_social_identity"),
            models.UniqueConstraint(fields=["provider", "user"], name="unique_provider_per_user"),
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} · {self.user}"
