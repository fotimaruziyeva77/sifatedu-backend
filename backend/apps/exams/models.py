"""Oylik imtihon: 20 ta test (saytda yoki botda, bitta urinish) + 5 ta amaliy topshiriq.

Imtihon kurs va oy bo'yicha. Test qismi dars testlari mexanizmida (savollar, aralashtirish,
baholash — `apps.quizzes`), lekin javob paytida to'g'ri/noto'g'ri aytilmaydi. Amaliy qism — uy
vazifasidagi kabi javob (izoh, kod, havola, fayllar), o'qituvchi 0–100 baholaydi.
"""

import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

MAX_TASKS = 5


class Exam(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Qoralama")
        READY = "READY", _("Tayyor")

    course = models.ForeignKey(
        "catalog.Course", verbose_name=_("kurs"), on_delete=models.CASCADE, related_name="exams"
    )
    month = models.DateField(_("oy"), help_text=_("Oyning birinchi kuni."))
    status = models.CharField(
        _("holat"),
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text=_("Tayyor bo'lmagan imtihon ochilmaydi."),
    )
    modules = models.ManyToManyField(
        "catalog.Module",
        verbose_name=_("modullar"),
        blank=True,
        related_name="+",
        help_text=_("Test savollari shu modullar darslarining testlaridan. Bo'sh — hammasidan."),
    )
    questions_count = models.PositiveSmallIntegerField(
        _("test savollari"), default=20, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    duration_min = models.PositiveSmallIntegerField(
        _("test vaqti (daqiqa)"),
        default=40,
        validators=[MinValueValidator(5), MaxValueValidator(240)],
    )
    pass_percent = models.PositiveSmallIntegerField(
        _("o'tish bali (%)"), default=60, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    test_weight = models.PositiveSmallIntegerField(
        _("test ulushi (%)"),
        default=50,
        validators=[MaxValueValidator(100)],
        help_text=_("Natijadagi test qismining ulushi; qolgani — amaliy topshiriqlar."),
    )
    opens_at = models.DateTimeField(_("ochiladi"))
    closes_at = models.DateTimeField(_("yopiladi"))
    opened_notified_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("muallif"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = _("oylik imtihon")
        verbose_name_plural = _("oylik imtihonlar")
        ordering = ("-month", "course__order", "course_id")
        constraints = [
            models.UniqueConstraint(fields=["course", "month"], name="unique_exam_per_month")
        ]

    def __str__(self) -> str:
        return f"{self.course} — {self.month:%Y-%m}"

    @property
    def is_ready(self) -> bool:
        return self.status == self.Status.READY

    def is_open(self, now: datetime | None = None) -> bool:
        now = now or timezone.now()
        return self.is_ready and self.opens_at <= now < self.closes_at


class ExamTask(models.Model):
    """Amaliy topshiriq (imtihonda 5 ta): o'quvchi kod, fayl, rasm yoki havola yuboradi."""

    exam = models.ForeignKey(
        Exam, verbose_name=_("imtihon"), on_delete=models.CASCADE, related_name="tasks"
    )
    order = models.PositiveSmallIntegerField(_("tartib"), default=0)
    title = models.CharField(_("sarlavha"), max_length=200)
    instructions = models.TextField(_("topshiriq"))

    class Meta:
        verbose_name = _("amaliy topshiriq")
        verbose_name_plural = _("amaliy topshiriqlar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title


class ExamExtension(models.Model):
    """Imtihonga kelolmagan o'quvchiga o'qituvchi bergan alohida muddat."""

    exam = models.ForeignKey(
        Exam, verbose_name=_("imtihon"), on_delete=models.CASCADE, related_name="extensions"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="+",
    )
    until = models.DateTimeField(_("muddat"))
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("bergan"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(_("berilgan"), auto_now_add=True)

    class Meta:
        verbose_name = _("alohida muddat")
        verbose_name_plural = _("alohida muddatlar")
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="unique_exam_extension")
        ]

    def __str__(self) -> str:
        return f"{self.student} · {self.exam}"


class ExamAttempt(models.Model):
    """Test qismi — bitta urinish. `question_ids` va `seed` — dars testidagi kabi."""

    exam = models.ForeignKey(
        Exam, verbose_name=_("imtihon"), on_delete=models.CASCADE, related_name="attempts"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="exam_attempts",
    )
    question_ids = models.JSONField(default=list, editable=False)
    seed = models.PositiveIntegerField(default=0, editable=False)
    started_at = models.DateTimeField(_("boshlangan"), auto_now_add=True)
    deadline = models.DateTimeField(_("vaqt tugaydi"))
    finished_at = models.DateTimeField(_("tugagan"), null=True, blank=True)
    score = models.PositiveSmallIntegerField(_("test natijasi (%)"), null=True, blank=True)

    class Meta:
        verbose_name = _("imtihon testi")
        verbose_name_plural = _("imtihon testlari")
        ordering = ("-started_at",)
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="unique_exam_attempt")
        ]

    def __str__(self) -> str:
        return f"{self.student} · {self.exam}"


class ExamAnswer(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt, verbose_name=_("urinish"), on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        "quizzes.Question", verbose_name=_("savol"), on_delete=models.CASCADE, related_name="+"
    )
    response = models.JSONField(_("javob"), default=dict)
    correct = models.BooleanField(_("to'g'ri"), default=False)
    answered_at = models.DateTimeField(_("vaqt"), auto_now_add=True)

    class Meta:
        verbose_name = _("imtihon javobi")
        verbose_name_plural = _("imtihon javoblari")
        ordering = ("answered_at", "id")
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_exam_answer")
        ]

    def __str__(self) -> str:
        return f"{self.attempt} · {self.question_id}"


class TaskAnswer(TimeStampedModel):
    """Amaliy topshiriq javobi. Baholanguncha qayta yuborish mumkin (oxirgisi qoladi)."""

    task = models.ForeignKey(
        ExamTask, verbose_name=_("topshiriq"), on_delete=models.CASCADE, related_name="answers"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="exam_task_answers",
    )
    text = models.TextField(_("izoh"), blank=True)
    code = models.TextField(_("kod"), blank=True)
    language = models.CharField(_("kod tili"), max_length=20, blank=True)
    link = models.URLField(_("havola"), max_length=500, blank=True)
    score = models.PositiveSmallIntegerField(
        _("baho"), null=True, blank=True, validators=[MaxValueValidator(100)]
    )
    feedback = models.TextField(_("o'qituvchi izohi"), blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("baholagan"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(_("baholangan"), null=True, blank=True)

    class Meta:
        verbose_name = _("amaliy topshiriq javobi")
        verbose_name_plural = _("amaliy topshiriq javoblari")
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(fields=["task", "student"], name="unique_task_answer")
        ]

    def __str__(self) -> str:
        return f"{self.student} · {self.task}"


def task_file_path(instance: "TaskAnswerFile", filename: str) -> str:
    suffix = Path(filename).suffix.lower()[:12]
    return f"exams/{instance.answer.task_id}/{uuid.uuid4().hex}{suffix}"


class TaskAnswerFile(models.Model):
    answer = models.ForeignKey(
        TaskAnswer, verbose_name=_("javob"), on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(_("fayl"), upload_to=task_file_path, max_length=255)
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


class ExamResult(models.Model):
    """O'quvchining imtihon natijasi. Imtihon (yoki alohida muddat) yopilib, topshirilgan amaliy
    javoblar baholangach — yakuniy (`final_at`): o'quvchiga xabar va sertifikat hisobida."""

    exam = models.ForeignKey(
        Exam, verbose_name=_("imtihon"), on_delete=models.CASCADE, related_name="results"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="exam_results",
    )
    test_score = models.PositiveSmallIntegerField(_("test (%)"), default=0)
    practical_score = models.PositiveSmallIntegerField(_("amaliy (%)"), default=0)
    total = models.PositiveSmallIntegerField(_("natija (%)"), default=0)
    passed = models.BooleanField(_("o'tdi"), default=False)
    final_at = models.DateTimeField(_("yakunlangan"), null=True, blank=True)

    class Meta:
        verbose_name = _("imtihon natijasi")
        verbose_name_plural = _("imtihon natijalari")
        ordering = ("-exam__month", "student_id")
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="unique_exam_result")
        ]

    def __str__(self) -> str:
        return f"{self.student} · {self.exam}: {self.total}%"
