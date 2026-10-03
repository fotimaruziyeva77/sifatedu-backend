"""Kursga kirish huquqi (Enrollment), o'qituvchi guruhlari va dars progressi."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

# Dars shu ulushdan ko'p ko'rilsa, tugatilgan hisoblanadi.
COMPLETE_RATIO = 0.9


class StudyGroup(TimeStampedModel):
    """O'qituvchining guruhi: bitta kurs o'quvchilari (offlayn — bir xonada, onlayn — bitta
    mentor bilan haftalik jonli dars). O'quvchi guruhga `Enrollment.group` orqali biriktiriladi."""

    class Status(models.TextChoices):
        FORMING = "FORMING", _("Yig'ilmoqda")
        ACTIVE = "ACTIVE", _("O'qiyapti")
        FINISHED = "FINISHED", _("Tugagan")

    name = models.CharField(_("nomi"), max_length=60, help_text=_("Masalan: FE-12 yoki Kids-3"))
    course = models.ForeignKey(
        "catalog.Course",
        verbose_name=_("kurs"),
        on_delete=models.PROTECT,
        related_name="study_groups",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'qituvchi"),
        on_delete=models.PROTECT,
        related_name="teaching_groups",
        limit_choices_to={"groups__name": "TEACHER"},
    )
    study_format = models.CharField(
        _("shakl"),
        max_length=10,
        choices=[("ONLINE", _("Onlayn")), ("OFFLINE", _("Offlayn"))],
        default="OFFLINE",
    )
    schedule = models.CharField(
        _("jadval"), max_length=120, blank=True, help_text=_("Masalan: Du, Chor, Ju — 18:00")
    )
    starts_on = models.DateField(_("boshlanish sanasi"), null=True, blank=True)
    # Jadvaldan yaratiladigan darslar shularni oladi (bitta darsda o'zgartirish mumkin).
    meet_url = models.URLField(
        _("doimiy Meet yoki Zoom havolasi"), blank=True, help_text=_("Onlayn guruh uchun.")
    )
    teacher_paced = models.BooleanField(
        _("darslarni o'qituvchi ochadi"),
        default=False,
        help_text=_(
            "Onlayn (Zoom, videosiz) guruh uchun: test va uy vazifalari o'qituvchi «Dars o'tildi» "
            "deb belgilagan darsgacha ochiladi, testdan o'tish sharti yo'q. Offlayn guruhda doim "
            "shunday."
        ),
    )
    room = models.CharField(
        _("xona"), max_length=60, blank=True, help_text=_("Offlayn guruh uchun.")
    )
    capacity = models.PositiveSmallIntegerField(_("o'rinlar soni"), null=True, blank=True)
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.FORMING, db_index=True
    )

    class Meta:
        verbose_name = _("guruh")
        verbose_name_plural = _("guruhlar")
        ordering = ("-starts_on", "name")
        constraints = [
            models.UniqueConstraint(fields=["course", "name"], name="unique_group_name_per_course"),
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.course}"


class Enrollment(TimeStampedModel):
    """Foydalanuvchining kursga kirish huquqi.

    Onlayn — bir martalik to'lov, `expires_at` bo'sh qoladi.
    Offlayn — oyma-oy to'lov: `expires_at` to'langan oy tugaydigan sana.
    """

    class Source(models.TextChoices):
        PAYMENT = "PAYMENT", _("To'lov")
        MANUAL = "MANUAL", _("Qo'lda berilgan")
        FREE = "FREE", _("Bepul kurs")

    class Format(models.TextChoices):
        ONLINE = "ONLINE", _("Onlayn")
        OFFLINE = "OFFLINE", _("Offlayn")

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Faol")
        CANCELLED = "CANCELLED", _("Bekor qilingan")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        "catalog.Course",
        verbose_name=_("kurs"),
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    source = models.CharField(
        _("manba"), max_length=10, choices=Source.choices, default=Source.MANUAL
    )
    study_format = models.CharField(
        _("shakl"), max_length=10, choices=Format.choices, default=Format.ONLINE
    )
    expires_at = models.DateTimeField(
        _("amal qilish muddati"),
        null=True,
        blank=True,
        help_text=_("Offlayn (oylik) to'lov uchun. Bo'sh bo'lsa — cheklanmagan."),
    )
    group = models.ForeignKey(
        StudyGroup,
        verbose_name=_("guruh"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollments",
    )

    class Meta:
        verbose_name = _("kursga yozilish")
        verbose_name_plural = _("kursga yozilishlar")
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_enrollment"),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.course}"

    def clean(self) -> None:
        group = self.group
        if group is not None and self.course_id and group.course_id != self.course_id:
            raise ValidationError({"group": _("Guruh boshqa kursniki.")})

    @property
    def is_open(self) -> bool:
        if self.status != self.Status.ACTIVE:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()


class LessonProgress(TimeStampedModel):
    """Dars qayerda qolgani va tugatilgani."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        "catalog.Lesson",
        verbose_name=_("dars"),
        on_delete=models.CASCADE,
        related_name="progress",
    )
    position_sec = models.PositiveIntegerField(_("to'xtagan joyi (soniya)"), default=0)
    watched_sec = models.PositiveIntegerField(_("ko'rilgan (soniya)"), default=0)
    completed_at = models.DateTimeField(_("tugatilgan"), null=True, blank=True)

    class Meta:
        verbose_name = _("dars progressi")
        verbose_name_plural = _("dars progressi")
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(fields=["user", "lesson"], name="unique_lesson_progress"),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.lesson}"

    @property
    def completed(self) -> bool:
        return self.completed_at is not None
