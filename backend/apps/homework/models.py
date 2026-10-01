"""Uy vazifalari: o'qituvchi darsga beradi, o'quvchi javob yuboradi, o'qituvchi baholaydi.

Har bir darsda bitta vazifa. O'quvchining har bir yuborishi — alohida urinish (`Submission`):
qaytarilgan bo'lsa, keyingisi yangi raqam bilan yoziladi, oldingilari tarixda qoladi.
"""

import uuid
from pathlib import Path

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Assignment(TimeStampedModel):
    lesson = models.OneToOneField(
        "catalog.Lesson",
        verbose_name=_("dars"),
        on_delete=models.CASCADE,
        related_name="assignment",
    )
    title = models.CharField(_("sarlavha"), max_length=200, default="Uy vazifasi")
    instructions = models.TextField(
        _("topshiriq"),
        help_text=_("Nima qilish va nimani yuborish kerak: kod, rasm, havola yoki fayl."),
    )
    deadline = models.DateTimeField(
        _("muddat"),
        null=True,
        blank=True,
        help_text=_(
            "Ixtiyoriy. Muddatdan keyin ham yuborish mumkin — javob «kechikkan» deb belgilanadi."
        ),
    )

    class Meta:
        verbose_name = _("uy vazifasi")
        verbose_name_plural = _("uy vazifalari")

    def __str__(self) -> str:
        return f"{self.lesson} — {self.title}"


class Submission(TimeStampedModel):
    """O'quvchining bitta urinishi: izoh, kod, havola va fayllar; o'qituvchining qarori."""

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", _("Tekshirilmoqda")
        CHANGES_REQUESTED = "CHANGES_REQUESTED", _("Qayta ishlash kerak")
        ACCEPTED = "ACCEPTED", _("Qabul qilindi")

    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("vazifa"),
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="homework_submissions",
    )
    attempt = models.PositiveSmallIntegerField(_("urinish"), default=1)
    status = models.CharField(
        _("holat"),
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )
    text = models.TextField(_("izoh"), blank=True)
    code = models.TextField(_("kod"), blank=True)
    language = models.CharField(_("kod tili"), max_length=20, blank=True)
    link = models.URLField(_("havola"), max_length=500, blank=True)
    late = models.BooleanField(_("kechikkan"), default=False)
    score = models.PositiveSmallIntegerField(
        _("baho"), null=True, blank=True, validators=[MaxValueValidator(100)]
    )
    feedback = models.TextField(_("o'qituvchi izohi"), blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("tekshirgan"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(_("tekshirilgan"), null=True, blank=True)

    class Meta:
        verbose_name = _("javob")
        verbose_name_plural = _("javoblar")
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student", "attempt"], name="unique_submission_attempt"
            )
        ]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.student} · {self.assignment} · #{self.attempt}"


def submission_path(instance: "SubmissionFile", filename: str) -> str:
    """Tasodifiy nom: havoladan o'quvchi yoki fayl nomini bilib bo'lmaydi."""
    suffix = Path(filename).suffix.lower()[:12]
    return f"homework/{instance.submission.assignment_id}/{uuid.uuid4().hex}{suffix}"


class SubmissionFile(models.Model):
    """Javobga ilova: rasm, arxiv, hujjat yoki kod fayli (yopiq bucket'da)."""

    submission = models.ForeignKey(
        Submission, verbose_name=_("javob"), on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(_("fayl"), upload_to=submission_path, max_length=255)
    name = models.CharField(_("nomi"), max_length=255)
    size = models.PositiveIntegerField(_("hajmi (bayt)"))
    content_type = models.CharField(_("turi"), max_length=100, blank=True)
    is_image = models.BooleanField(_("rasm"), default=False)
    created_at = models.DateTimeField(_("yuklangan"), auto_now_add=True)

    class Meta:
        verbose_name = _("javob fayli")
        verbose_name_plural = _("javob fayllari")
        ordering = ("id",)

    def __str__(self) -> str:
        return self.name
