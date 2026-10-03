"""Guruhlarga kunlik test: har kuni 07:00 da ochiladi, 23:00 da yopiladi.

Savollar — guruhda o'tilgan darslar («Dars o'tildi») testlaridan, har o'quvchiga o'zicha tasodifiy
tanlanadi. Javob paytida to'g'ri/noto'g'ri aytilmaydi; oxirida — nechta to'g'ri va noto'g'ri, XP va
coin. To'g'ri javoblar va izohlar test yopilgach. Bajarmaganga jarima yo'q.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class DailyTest(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", _("Ochiq")
        CLOSED = "CLOSED", _("Yopilgan")
        SKIPPED = "SKIPPED", _("Savollar yetarli emas")

    group = models.ForeignKey(
        "learning.StudyGroup",
        verbose_name=_("guruh"),
        on_delete=models.CASCADE,
        related_name="daily_tests",
    )
    day = models.DateField(_("kun"), db_index=True)
    status = models.CharField(
        _("holat"), max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    questions_count = models.PositiveSmallIntegerField(_("savollar soni"), default=20)
    pool_size = models.PositiveIntegerField(
        _("savollar banki"), default=0, help_text=_("O'tilgan darslar testlaridagi savollar.")
    )
    opens_at = models.DateTimeField(_("ochiladi"))
    closes_at = models.DateTimeField(_("yopiladi"))

    class Meta:
        verbose_name = _("kunlik test")
        verbose_name_plural = _("kunlik testlar")
        ordering = ("-day", "group_id")
        constraints = [
            models.UniqueConstraint(fields=["group", "day"], name="unique_daily_test_per_day")
        ]

    def __str__(self) -> str:
        return f"{self.group} · {self.day:%d.%m.%Y}"


class DailyAttempt(models.Model):
    test = models.ForeignKey(
        DailyTest, verbose_name=_("test"), on_delete=models.CASCADE, related_name="attempts"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="daily_attempts",
    )
    question_ids = models.JSONField(default=list, editable=False)
    seed = models.PositiveIntegerField(default=0, editable=False)
    started_at = models.DateTimeField(_("boshlangan"), auto_now_add=True)
    finished_at = models.DateTimeField(_("tugagan"), null=True, blank=True)
    correct = models.PositiveSmallIntegerField(_("to'g'ri"), default=0)
    total = models.PositiveSmallIntegerField(_("savollar"), default=0)

    class Meta:
        verbose_name = _("kunlik test natijasi")
        verbose_name_plural = _("kunlik test natijalari")
        ordering = ("-started_at",)
        constraints = [
            models.UniqueConstraint(fields=["test", "student"], name="unique_daily_attempt")
        ]

    def __str__(self) -> str:
        return f"{self.student} · {self.correct}/{self.total}"


class DailyAnswer(models.Model):
    attempt = models.ForeignKey(DailyAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("quizzes.Question", on_delete=models.CASCADE, related_name="+")
    response = models.JSONField(_("javob"), default=dict)
    correct = models.BooleanField(_("to'g'ri"), default=False)
    answered_at = models.DateTimeField(_("vaqt"), auto_now_add=True)

    class Meta:
        verbose_name = _("javob")
        verbose_name_plural = _("javoblar")
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_daily_answer")
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id}:{self.question_id}"
