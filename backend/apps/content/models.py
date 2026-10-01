"""Landing va ommaviy sahifalar matnlari. Hammasi admin paneldan 3 tilda tahrirlanadi (TZ 4.1)."""

from typing import Any

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from apps.core.html import sanitize_html
from apps.core.models import TimeStampedModel
from apps.core.storage import public_storage
from apps.core.validators import MaxFileSizeValidator

PROMO_VIDEO_MAX_MB = 200


class SiteSettings(models.Model):
    """Yagona yozuv (pk=1): hero matnlari, kontaktlar va bo'limlar ko'rinishi."""

    hero_title = models.CharField(
        _("hero sarlavhasi"),
        max_length=200,
        help_text=_("Ajratib ko'rsatiladigan so'zni yulduzchalar ichiga oling: *kod*"),
    )
    hero_subtitle = models.TextField(_("hero matni"), blank=True)

    about_text = models.TextField(
        _("biz haqimizda"),
        blank=True,
        help_text=_("«Biz kimmiz» bo'limidagi manifest: 2–4 gap."),
    )
    promo_video = models.FileField(
        _("promo video"),
        storage=public_storage,
        upload_to="promo/",
        blank=True,
        validators=[
            FileExtensionValidator(["mp4", "webm"]),
            MaxFileSizeValidator(PROMO_VIDEO_MAX_MB),
        ],
        help_text=format_lazy(
            _(
                "MP4 (H.264) yoki WebM, {limit} MB gacha. Bo'lmasa, saytda animatsion rolik "
                "ko'rsatiladi."
            ),
            limit=PROMO_VIDEO_MAX_MB,
        ),
    )
    promo_poster = models.ImageField(
        _("video muqovasi"),
        storage=public_storage,
        upload_to="promo/",
        blank=True,
        help_text=_("Video boshlanishidan oldin ko'rinadigan rasm (16:9)."),
    )

    phone = models.CharField(_("telefon"), max_length=20, blank=True)
    email = models.EmailField(_("email"), blank=True)
    address = models.CharField(_("manzil"), max_length=255, blank=True)
    working_hours = models.CharField(_("ish vaqti"), max_length=100, blank=True)

    telegram_url = models.URLField(_("Telegram"), blank=True)
    instagram_url = models.URLField(_("Instagram"), blank=True)
    youtube_url = models.URLField(_("YouTube"), blank=True)
    facebook_url = models.URLField(_("Facebook"), blank=True)

    show_stats = models.BooleanField(_("raqamlar bo'limi"), default=True)
    show_instructors = models.BooleanField(_("ustozlar bo'limi"), default=True)
    show_testimonials = models.BooleanField(
        _("fikrlar bo'limi"),
        default=True,
        help_text=_("Nashr qilingan fikr bo'lmasa, bo'lim baribir ko'rinmaydi."),
    )

    updated_at = models.DateTimeField(_("yangilangan"), auto_now=True)

    DEFAULT_HERO_TITLE = "Sifat Edu"

    class Meta:
        verbose_name = _("sayt sozlamalari")
        verbose_name_plural = _("sayt sozlamalari")

    def __str__(self) -> str:
        return str(_("Sayt sozlamalari"))

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSettings":
        obj, _created = cls.objects.get_or_create(
            pk=1, defaults={"hero_title": cls.DEFAULT_HERO_TITLE}
        )
        return obj


class OrderedContent(TimeStampedModel):
    order = models.PositiveIntegerField(_("tartib"), default=0)
    is_published = models.BooleanField(_("saytda ko'rinadi"), default=True)

    class Meta:
        abstract = True
        ordering = ("order", "id")


class Advantage(OrderedContent):
    class Icon(models.TextChoices):
        VIDEO = "video", "Video"
        CODE = "code", "Code"
        USERS = "users", "Users"
        LANGUAGES = "languages", "Languages"
        WIFI = "wifi", "Wifi"
        INFINITY = "infinity", "Infinity"
        AWARD = "award", "Award"
        HEADPHONES = "headphones", "Headphones"
        ACCESSIBILITY = "accessibility", "Accessibility"
        ROCKET = "rocket", "Rocket"

    icon = models.CharField(_("belgi"), max_length=20, choices=Icon.choices, default=Icon.CODE)
    title = models.CharField(_("sarlavha"), max_length=120)
    text = models.TextField(_("matn"), blank=True)

    class Meta(OrderedContent.Meta):
        verbose_name = _("afzallik")
        verbose_name_plural = _("afzalliklar")

    def __str__(self) -> str:
        return self.title


class Concern(OrderedContent):
    """O'quvchini to'xtatib turadigan xavotir va unga javob ("Sizga ham tanishmi?")."""

    problem = models.CharField(_("xavotir"), max_length=120)
    answer = models.CharField(_("javob"), max_length=240)

    class Meta(OrderedContent.Meta):
        verbose_name = _("xavotir")
        verbose_name_plural = _("xavotirlar")

    def __str__(self) -> str:
        return self.problem


class HowStep(OrderedContent):
    title = models.CharField(_("sarlavha"), max_length=120)
    text = models.TextField(_("matn"), blank=True)

    class Meta(OrderedContent.Meta):
        verbose_name = _("qadam")
        verbose_name_plural = _('"Qanday ishlaydi" qadamlari')

    def __str__(self) -> str:
        return self.title


class FAQItem(OrderedContent):
    question = models.CharField(_("savol"), max_length=255)
    answer = models.TextField(_("javob"))

    class Meta(OrderedContent.Meta):
        verbose_name = _("savol-javob")
        verbose_name_plural = _("FAQ")

    def __str__(self) -> str:
        return self.question


class Testimonial(OrderedContent):
    """Faqat haqiqiy fikrlar (TZ 4.1): nashr qilingani bo'lmasa, bo'lim ko'rinmaydi."""

    author_name = models.CharField(_("muallif"), max_length=120)
    author_role = models.CharField(
        _("kim"), max_length=150, blank=True, help_text=_("Masalan: Frontend kursi bitiruvchisi")
    )
    text = models.TextField(_("fikr"))
    avatar = models.ImageField(
        _("rasm"), storage=public_storage, upload_to="testimonials/", blank=True
    )
    # Yangi fikr admin tekshirmaguncha saytda ko'rinmaydi.
    is_published = models.BooleanField(_("saytda ko'rinadi"), default=False)

    class Meta(OrderedContent.Meta):
        verbose_name = _("fikr")
        verbose_name_plural = _("fikrlar")

    def __str__(self) -> str:
        return self.author_name


class LegalPage(TimeStampedModel):
    class Slug(models.TextChoices):
        OFFER = "offer", _("Ommaviy oferta")
        PRIVACY = "privacy", _("Maxfiylik siyosati")
        REFUND = "refund-policy", _("Pulni qaytarish qoidalari")

    slug = models.SlugField(_("sahifa"), unique=True, choices=Slug.choices)
    title = models.CharField(_("sarlavha"), max_length=200)
    body = models.TextField(_("matn"))
    version = models.CharField(_("versiya"), max_length=20, default="1.0")

    class Meta:
        verbose_name = _("huquqiy sahifa")
        verbose_name_plural = _("huquqiy sahifalar")
        ordering = ("slug",)

    def __str__(self) -> str:
        return self.title

    def save(self, *args: Any, **kwargs: Any) -> None:
        for code, _name in settings.LANGUAGES:
            field = f"body_{code}"
            value = getattr(self, field, None)
            if value:
                setattr(self, field, sanitize_html(value))
        super().save(*args, **kwargs)
