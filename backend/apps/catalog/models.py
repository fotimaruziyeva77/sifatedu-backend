"""Katalog: kategoriya → kurs → modul → dars. Video va materiallar 4-qadamda qo'shiladi."""

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.html import sanitize_html
from apps.core.models import TimeStampedModel
from apps.core.storage import public_storage


class Category(TimeStampedModel):
    slug = models.SlugField(_("slug"), unique=True)
    name = models.CharField(_("nomi"), max_length=100)
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("kategoriya")
        verbose_name_plural = _("kategoriyalar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.name


class Instructor(TimeStampedModel):
    slug = models.SlugField(_("slug"), unique=True)
    full_name = models.CharField(_("ism-familiya"), max_length=150)
    position = models.CharField(
        _("lavozim"), max_length=150, blank=True, help_text=_("Masalan: Senior Frontend Developer")
    )
    bio = models.TextField(_("qisqacha ma'lumot"), blank=True)
    photo = models.ImageField(
        _("rasm"), storage=public_storage, upload_to="instructors/", blank=True
    )
    experience_years = models.PositiveSmallIntegerField(_("tajriba (yil)"), null=True, blank=True)
    telegram_url = models.URLField(_("Telegram"), blank=True)
    linkedin_url = models.URLField(_("LinkedIn"), blank=True)
    github_url = models.URLField(_("GitHub"), blank=True)
    # 2-bosqichda ustoz platformada o'z akkaunti bilan ishlaydi.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("akkaunt"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instructor_profile",
    )
    order = models.PositiveIntegerField(_("tartib"), default=0)
    is_published = models.BooleanField(_("saytda ko'rinadi"), default=True)

    class Meta:
        verbose_name = _("ustoz")
        verbose_name_plural = _("ustozlar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.full_name


class Course(TimeStampedModel):
    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", _("Boshlang'ich")
        INTERMEDIATE = "INTERMEDIATE", _("O'rta")
        ADVANCED = "ADVANCED", _("Yuqori")

    class Audience(models.TextChoices):
        ADULT = "ADULT", _("15 yoshdan kattalar")
        KIDS = "KIDS", _("Bolalar (7–11 yosh)")

    class Format(models.TextChoices):
        ONLINE = "ONLINE", _("Onlayn")
        OFFLINE = "OFFLINE", _("Offlayn")
        BOTH = "BOTH", _("Onlayn va offlayn")

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Qoralama")
        PUBLISHED = "PUBLISHED", _("Nashr qilingan")
        ARCHIVED = "ARCHIVED", _("Arxivda")

    class Icon(models.TextChoices):
        CODE = "code", "Code"
        SERVER = "server", "Server"
        DATABASE = "database", "Database"
        PALETTE = "palette", "Palette"
        SMARTPHONE = "smartphone", "Smartphone"
        BRAIN = "brain", "Brain"
        TERMINAL = "terminal", "Terminal"
        SHIELD = "shield", "Shield"
        BLOCKS = "blocks", "Blocks"
        MONITOR = "monitor", "Monitor"
        LANGUAGES = "languages", "Languages"

    slug = models.SlugField(_("slug"), unique=True)
    title = models.CharField(_("nomi"), max_length=200)
    short_description = models.CharField(_("qisqa tavsif"), max_length=300, blank=True)
    description = models.TextField(_("to'liq tavsif"), blank=True)
    category = models.ForeignKey(
        Category, verbose_name=_("kategoriya"), on_delete=models.PROTECT, related_name="courses"
    )
    instructors = models.ManyToManyField(
        Instructor, verbose_name=_("ustozlar"), blank=True, related_name="courses"
    )
    level = models.CharField(
        _("daraja"), max_length=20, choices=Level.choices, default=Level.BEGINNER
    )
    status = models.CharField(
        _("holat"), max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    audience = models.CharField(
        _("kimga"),
        max_length=10,
        choices=Audience.choices,
        default=Audience.ADULT,
        db_index=True,
        help_text=_("Kabinet ko'rinishi va katalog filtri shu qiymatga bog'liq."),
    )
    age_min = models.PositiveSmallIntegerField(_("eng kichik yosh"), null=True, blank=True)
    age_max = models.PositiveSmallIntegerField(_("eng katta yosh"), null=True, blank=True)
    study_format = models.CharField(
        _("o'qish shakli"), max_length=10, choices=Format.choices, default=Format.ONLINE
    )
    is_free = models.BooleanField(
        _("bepul"),
        default=False,
        help_text=_("Bepul kursni ro'yxatdan o'tgan har kim o'qiy oladi."),
    )
    # Onlayn: bir martalik to'lov. Offlayn: oyma-oy to'lov (abonement).
    price_online = models.PositiveIntegerField(_("onlayn narx (bir marta, so'm)"), default=0)
    price_offline_monthly = models.PositiveIntegerField(_("offlayn narx (oyiga, so'm)"), default=0)
    video_language = models.CharField(
        _("video tili"), max_length=2, choices=settings.LANGUAGES, default="uz"
    )
    duration_hours = models.PositiveSmallIntegerField(
        _("davomiyligi (soat)"), null=True, blank=True
    )
    icon = models.CharField(
        _("belgi"),
        max_length=20,
        choices=Icon.choices,
        default=Icon.CODE,
        help_text=_("Muqova rasmi bo'lmasa, kartochkada ko'rsatiladi."),
    )
    cover = models.ImageField(_("muqova"), storage=public_storage, upload_to="courses/", blank=True)
    mxik_code = models.CharField(
        _("MXIK (IKPU) kodi"),
        max_length=20,
        blank=True,
        help_text=_("Fiskal chek uchun. Soliq qo'mitasi ro'yxatidan olinadi."),
    )
    is_featured = models.BooleanField(
        _("bosh sahifada"),
        default=False,
        help_text=_("Landing'dagi kurslar bo'limida ko'rsatiladi."),
    )
    order = models.PositiveIntegerField(_("tartib"), default=0)
    monthly_exam = models.BooleanField(
        _("oylik imtihon"),
        default=False,
        help_text=_(
            "Har oyning 20-kuni imtihon qoralamasi o'zi yaratiladi; 25-kundan oy oxirigacha ochiq."
        ),
    )
    certificate = models.BooleanField(
        _("sertifikat beriladi"),
        default=True,
        help_text=_(
            "Darslar, testlar, uy vazifalari va imtihonlar shartlari bajarilganda o'zi beriladi."
        ),
    )

    # Dastur o'zgarganda signal orqali yangilanadi: katalogda har kurs uchun alohida
    # so'rov bo'lmasligi uchun shu yerda saqlanadi (apps/catalog/signals.py).
    lesson_count = models.PositiveIntegerField(_("darslar soni"), default=0, editable=False)
    total_duration_min = models.PositiveIntegerField(
        _("dastur davomiyligi (daqiqa)"), default=0, editable=False
    )

    class Meta:
        verbose_name = _("kurs")
        verbose_name_plural = _("kurslar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Tavsif admin'dagi HTML muharrirdan keladi: har bir tildagi qiymat tozalanadi.
        for code, _name in settings.LANGUAGES:
            field = f"description_{code}"
            value = getattr(self, field, None)
            if value:
                setattr(self, field, sanitize_html(value))
        super().save(*args, **kwargs)


class Module(TimeStampedModel):
    """Kurs dasturining bo'limi: ichida darslar."""

    course = models.ForeignKey(
        Course, verbose_name=_("kurs"), on_delete=models.CASCADE, related_name="modules"
    )
    title = models.CharField(_("nomi"), max_length=200)
    summary = models.CharField(_("qisqacha"), max_length=300, blank=True)
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("modul")
        verbose_name_plural = _("modullar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title


def material_path(instance: "LessonMaterial", filename: str) -> str:
    return f"lesson-materials/{instance.lesson_id}/{uuid.uuid4().hex}/{filename}"


class Lesson(TimeStampedModel):
    """Dars: video va qisqa tavsif."""

    module = models.ForeignKey(
        Module, verbose_name=_("modul"), on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(_("nomi"), max_length=200)
    summary = models.CharField(_("qisqacha"), max_length=300, blank=True)
    video = models.ForeignKey(
        "videos.VideoAsset",
        verbose_name=_("video"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
    )
    duration_min = models.PositiveSmallIntegerField(
        _("davomiyligi (daqiqa)"),
        default=0,
        help_text=_("Dastur va kurs hajmini ko'rsatish uchun."),
    )
    is_preview = models.BooleanField(
        _("bepul dars"),
        default=False,
        help_text=_("Sotib olmagan foydalanuvchi ham ko'ra oladi."),
    )
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("dars")
        verbose_name_plural = _("darslar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title


class LessonMaterial(TimeStampedModel):
    """Dars materiali: fayl (slayd, PDF, arxiv), havola yoki darsda yozilgan kod.

    Fayllar yopiq bucket'da turadi va faqat darsga kirish huquqi bor o'quvchiga qisqa
    muddatli havola bilan beriladi.
    """

    class Kind(models.TextChoices):
        FILE = "FILE", _("Fayl")
        LINK = "LINK", _("Havola")
        CODE = "CODE", _("Kod")

    lesson = models.ForeignKey(
        Lesson, verbose_name=_("dars"), on_delete=models.CASCADE, related_name="materials"
    )
    kind = models.CharField(_("turi"), max_length=10, choices=Kind.choices, default=Kind.FILE)
    title = models.CharField(_("nomi"), max_length=200)
    file = models.FileField(_("fayl"), upload_to=material_path, blank=True)
    url = models.URLField(_("havola"), blank=True)
    code = models.TextField(_("kod"), blank=True)
    language = models.CharField(
        _("dasturlash tili"),
        max_length=30,
        blank=True,
        help_text=_("Masalan: html, css, javascript, python."),
    )
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("dars materiali")
        verbose_name_plural = _("dars materiallari")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        required = {
            self.Kind.FILE: ("file", _("Faylni yuklang.")),
            self.Kind.LINK: ("url", _("Havolani kiriting.")),
            self.Kind.CODE: ("code", _("Kodni kiriting.")),
        }
        field, message = required[self.Kind(self.kind)]
        if not getattr(self, field):
            raise ValidationError({field: message})
