"""Daraja testi: botga yangi kelgan odam yo'nalishni tanlab, qisqa test ishlaydi va chegirma
kuponi oladi (yaxshi natija — katta chegirma), ariza esa menejerga tushadi.

Savollar — xizmat kursidagi dars testidan (`quiz`): bu kursga hech kim yozilmaydi, shuning uchun
savollarni oldindan ko'rib bo'lmaydi va ular dars dasturi, kunlik topshiriqlarga aralashmaydi.
Test botda, vaqtli; javob paytida to'g'ri yoki noto'g'riligi aytilmaydi.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class PlacementTest(TimeStampedModel):
    course = models.ForeignKey(
        "catalog.Course",
        verbose_name=_("yo'nalish (kurs)"),
        on_delete=models.CASCADE,
        related_name="placement_tests",
        help_text=_("Natija va ariza shu kurs bo'yicha."),
    )
    title = models.CharField(
        _("nomi"), max_length=60, help_text=_("Botdagi tugma, masalan: Python yoki Frontend.")
    )
    quiz = models.ForeignKey(
        "quizzes.Quiz",
        verbose_name=_("savollar"),
        on_delete=models.PROTECT,
        related_name="+",
        help_text=_(
            "Dars testi (savollar banki). O'quvchilarga ko'rinmasligi uchun xizmat kursida "
            "(masalan, «Daraja testlari») saqlang."
        ),
    )
    questions_count = models.PositiveSmallIntegerField(
        _("savollar soni"), default=12, validators=[MinValueValidator(3), MaxValueValidator(50)]
    )
    duration_min = models.PositiveSmallIntegerField(
        _("vaqt (daqiqa)"), default=15, validators=[MinValueValidator(3), MaxValueValidator(60)]
    )
    is_active = models.BooleanField(_("faol"), default=True)
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("daraja testi")
        verbose_name_plural = _("daraja testlari")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title


class PlacementAttempt(models.Model):
    test = models.ForeignKey(
        PlacementTest, verbose_name=_("test"), on_delete=models.CASCADE, related_name="attempts"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("foydalanuvchi"),
        on_delete=models.CASCADE,
        related_name="placement_attempts",
    )
    question_ids = models.JSONField(default=list, editable=False)
    seed = models.PositiveIntegerField(default=0, editable=False)
    started_at = models.DateTimeField(_("boshlangan"), auto_now_add=True, db_index=True)
    deadline = models.DateTimeField(_("vaqt tugaydi"))
    finished_at = models.DateTimeField(_("tugagan"), null=True, blank=True)
    score = models.PositiveSmallIntegerField(_("natija (%)"), null=True, blank=True)
    coupon = models.ForeignKey(
        "rewards.Coupon",
        verbose_name=_("kupon"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = _("daraja testi natijasi")
        verbose_name_plural = _("daraja testi natijalari")
        ordering = ("-started_at",)
        indexes = [models.Index(fields=["user", "test"])]

    def __str__(self) -> str:
        return f"{self.user} · {self.test} · {self.score if self.score is not None else '—'}%"


class PlacementAnswer(models.Model):
    attempt = models.ForeignKey(PlacementAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("quizzes.Question", on_delete=models.CASCADE, related_name="+")
    response = models.JSONField(_("javob"), default=dict)
    correct = models.BooleanField(_("to'g'ri"), default=False)
    answered_at = models.DateTimeField(_("vaqt"), auto_now_add=True)

    class Meta:
        verbose_name = _("javob")
        verbose_name_plural = _("javoblar")
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_placement_answer")
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id}:{self.question_id}"
