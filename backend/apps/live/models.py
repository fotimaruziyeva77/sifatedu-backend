"""Guruhlarning jonli (onlayn — Meet/Zoom) va offlayn darslari, jadvali va davomati.

Guruhga haftalik jadval (`ScheduleSlot`) qo'yiladi — darslar (`LiveLesson`) undan 14 kun oldinga
o'zi yaratiladi. O'qituvchi har darsda davomatni (`Attendance`) belgilaydi.
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

# Onlayn darsga shuncha oldin qo'shilish mumkin.
JOIN_BEFORE = timedelta(minutes=15)


class ScheduleSlot(models.Model):
    """Guruhning haftalik jadvalidagi bitta dars: hafta kuni, soat va davomiylik."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, _("Dushanba")
        TUESDAY = 1, _("Seshanba")
        WEDNESDAY = 2, _("Chorshanba")
        THURSDAY = 3, _("Payshanba")
        FRIDAY = 4, _("Juma")
        SATURDAY = 5, _("Shanba")
        SUNDAY = 6, _("Yakshanba")

    group = models.ForeignKey(
        "learning.StudyGroup",
        verbose_name=_("guruh"),
        on_delete=models.CASCADE,
        related_name="slots",
    )
    weekday = models.PositiveSmallIntegerField(_("hafta kuni"), choices=Weekday.choices)
    starts_at = models.TimeField(_("boshlanishi"))
    duration_min = models.PositiveSmallIntegerField(
        _("davomiyligi (daqiqa)"),
        default=90,
        validators=[MinValueValidator(15), MaxValueValidator(480)],
    )

    class Meta:
        verbose_name = _("jadvaldagi dars")
        verbose_name_plural = _("haftalik jadval")
        ordering = ("weekday", "starts_at")
        constraints = [
            models.UniqueConstraint(
                fields=["group", "weekday", "starts_at"], name="unique_schedule_slot"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_weekday_display()} {self.starts_at:%H:%M}"


class LiveLesson(TimeStampedModel):
    class Kind(models.TextChoices):
        ONLINE = "ONLINE", _("Onlayn")
        OFFLINE = "OFFLINE", _("Offlayn")

    group = models.ForeignKey(
        "learning.StudyGroup",
        verbose_name=_("guruh"),
        on_delete=models.CASCADE,
        related_name="live_lessons",
    )
    starts_at = models.DateTimeField(_("boshlanishi"), db_index=True)
    duration_min = models.PositiveSmallIntegerField(
        _("davomiyligi (daqiqa)"),
        default=90,
        validators=[MinValueValidator(15), MaxValueValidator(480)],
    )
    kind = models.CharField(_("shakl"), max_length=10, choices=Kind.choices, default=Kind.ONLINE)
    meet_url = models.URLField(
        _("Meet yoki Zoom havolasi"), blank=True, help_text=_("Onlayn dars uchun.")
    )
    room = models.CharField(
        _("xona"), max_length=60, blank=True, help_text=_("Offlayn dars uchun, masalan: 3-xona.")
    )
    topic = models.ForeignKey(
        "catalog.Lesson",
        verbose_name=_("mavzu (dars)"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    title = models.CharField(_("sarlavha"), max_length=200, blank=True)
    notes = models.TextField(
        _("izoh"),
        blank=True,
        help_text=_("O'quvchilarga ko'rinadi: nima o'tildi, nima tayyorlash."),
    )
    recording_url = models.URLField(
        _("yozuv havolasi"), blank=True, help_text=_("YouTube (yopiq), Google Drive va h.k.")
    )
    canceled_at = models.DateTimeField(_("bekor qilingan"), null=True, blank=True)
    cancel_reason = models.CharField(_("bekor qilish sababi"), max_length=200, blank=True)
    # Jadvaldan avtomatik yaratilgan va qo'lda o'zgartirilmagan: jadval o'zgarsa qayta yaratiladi.
    generated = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = _("jonli dars")
        verbose_name_plural = _("jonli darslar")
        ordering = ("starts_at",)
        constraints = [
            models.UniqueConstraint(fields=["group", "starts_at"], name="unique_live_lesson_time")
        ]

    def __str__(self) -> str:
        return f"{self.group.name} · {self.starts_at:%d.%m %H:%M}"

    @property
    def ends_at(self) -> datetime:
        return self.starts_at + timedelta(minutes=self.duration_min)

    @property
    def opens_at(self) -> datetime:
        """Shu vaqtdan "Qo'shilish" ochiladi va davomatni belgilash mumkin."""
        return self.starts_at - JOIN_BEFORE

    @property
    def is_canceled(self) -> bool:
        return self.canceled_at is not None


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", _("Keldi")
        LATE = "LATE", _("Kechikdi")
        ABSENT = "ABSENT", _("Kelmadi")
        EXCUSED = "EXCUSED", _("Sababli")

    live_lesson = models.ForeignKey(
        LiveLesson, verbose_name=_("dars"), on_delete=models.CASCADE, related_name="attendance"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="attendance",
    )
    # Bo'sh — hali belgilanmagan.
    status = models.CharField(_("holat"), max_length=10, choices=Status.choices, blank=True)
    joined_at = models.DateTimeField(
        _("qo'shildi"), null=True, blank=True, help_text=_('"Qo\'shilish" bosilgan vaqt.')
    )
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("belgiladi"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    marked_at = models.DateTimeField(_("belgilangan"), null=True, blank=True)

    class Meta:
        verbose_name = _("davomat")
        verbose_name_plural = _("davomat")
        ordering = ("live_lesson", "student")
        constraints = [
            models.UniqueConstraint(fields=["live_lesson", "student"], name="unique_attendance")
        ]

    def __str__(self) -> str:
        return f"{self.live_lesson} · {self.student}"


class GroupLesson(models.Model):
    """Offlayn guruhda o'tilgan dars: shu darsgacha bo'lgan test va uy vazifalari guruh
    o'quvchilariga ochiladi (ustoz "Dars o'tildi" deb belgilaydi)."""

    group = models.ForeignKey(
        "learning.StudyGroup",
        verbose_name=_("guruh"),
        on_delete=models.CASCADE,
        related_name="covered_lessons",
    )
    lesson = models.ForeignKey(
        "catalog.Lesson", verbose_name=_("dars"), on_delete=models.CASCADE, related_name="+"
    )
    live_lesson = models.ForeignKey(
        LiveLesson,
        verbose_name=_("jonli dars"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="covered",
    )
    opened_at = models.DateTimeField(_("ochilgan"), auto_now_add=True)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("kim ochdi"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = _("o'tilgan dars")
        verbose_name_plural = _("o'tilgan darslar")
        ordering = ("-opened_at",)
        constraints = [
            models.UniqueConstraint(fields=["group", "lesson"], name="unique_group_lesson")
        ]

    def __str__(self) -> str:
        return f"{self.group.name} · {self.lesson}"
