"""Dars testlari va o'yinli mashqlar: o'quvchi darsni tushunganini tekshiradi.

Test darsga bog'lanadi (modul testi — videosiz, faqat testli dars). Har bir urinish serverda
baholanadi: brauzerga savollar javobsiz boradi, har bir javob alohida tekshiriladi.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Quiz(TimeStampedModel):
    lesson = models.OneToOneField(
        "catalog.Lesson", verbose_name=_("dars"), on_delete=models.CASCADE, related_name="quiz"
    )
    title = models.CharField(_("sarlavha"), max_length=200, default="Darsni tekshiring")
    pass_percent = models.PositiveSmallIntegerField(
        _("o'tish bali (%)"),
        default=70,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    questions_per_attempt = models.PositiveSmallIntegerField(
        _("har urinishda savollar"),
        default=0,
        help_text=_("0 — hammasi. Aks holda savollar bankidan tasodifiy shuncha savol."),
    )
    shuffle_questions = models.BooleanField(_("savollar tartibini aralashtirish"), default=True)

    class Meta:
        verbose_name = _("test")
        verbose_name_plural = _("testlar")

    def __str__(self) -> str:
        return f"{self.lesson} — {self.title}"


class Question(models.Model):
    class Kind(models.TextChoices):
        SINGLE = "SINGLE", _("Bitta to'g'ri javob")
        MULTIPLE = "MULTIPLE", _("Bir nechta to'g'ri javob")
        TEXT = "TEXT", _("Matn bilan javob")
        ORDER = "ORDER", _("Tartiblash")
        MATCH = "MATCH", _("Moslashtirish")

    quiz = models.ForeignKey(
        Quiz, verbose_name=_("test"), on_delete=models.CASCADE, related_name="questions"
    )
    kind = models.CharField(_("turi"), max_length=10, choices=Kind.choices, default=Kind.SINGLE)
    text = models.TextField(_("savol"))
    code = models.TextField(
        _("kod"), blank=True, help_text=_("Ixtiyoriy: savol ostida ko'rsatiladigan kod parchasi.")
    )
    language = models.CharField(_("kod tili"), max_length=20, blank=True)
    explanation = models.TextField(
        _("izoh"), blank=True, help_text=_("Javobdan keyin ko'rsatiladi: nega aynan shu javob.")
    )
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("savol")
        verbose_name_plural = _("savollar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.text[:80]


class Choice(models.Model):
    """Variant. Turga qarab ma'nosi: to'g'ri/noto'g'ri variant, qabul qilinadigan matn javob,
    tartiblashdagi qadam (`order` — to'g'ri o'rni) yoki moslashtirishdagi juft (`match`)."""

    question = models.ForeignKey(
        Question, verbose_name=_("savol"), on_delete=models.CASCADE, related_name="choices"
    )
    text = models.CharField(_("matn"), max_length=500)
    is_correct = models.BooleanField(_("to'g'ri"), default=False)
    match = models.CharField(
        _("juft (o'ng tomon)"),
        max_length=500,
        blank=True,
        help_text=_("Faqat moslashtirish uchun."),
    )
    order = models.PositiveIntegerField(_("tartib"), default=0)

    class Meta:
        verbose_name = _("variant")
        verbose_name_plural = _("variantlar")
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.text[:80]


class Attempt(models.Model):
    """O'quvchining bitta urinishi. `question_ids` — shu urinishda berilgan savollar tartibi,
    `seed` — variantlar aralashtirilishi (sahifa yangilansa ham bir xil qoladi)."""

    quiz = models.ForeignKey(
        Quiz, verbose_name=_("test"), on_delete=models.CASCADE, related_name="attempts"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    question_ids = models.JSONField(default=list, editable=False)
    seed = models.PositiveIntegerField(default=0, editable=False)
    started_at = models.DateTimeField(_("boshlangan"), auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(_("tugagan"), null=True, blank=True)
    score = models.PositiveSmallIntegerField(_("natija (%)"), null=True, blank=True)
    stars = models.PositiveSmallIntegerField(_("yulduzlar"), default=0)
    passed = models.BooleanField(_("o'tdi"), default=False)

    class Meta:
        verbose_name = _("test urinishi")
        verbose_name_plural = _("test natijalari")
        ordering = ("-started_at",)
        indexes = [models.Index(fields=["student", "quiz"])]

    def __str__(self) -> str:
        return f"{self.student} · {self.quiz}"


class Answer(models.Model):
    attempt = models.ForeignKey(
        Attempt, verbose_name=_("urinish"), on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        Question, verbose_name=_("savol"), on_delete=models.CASCADE, related_name="answers"
    )
    response = models.JSONField(_("javob"), default=dict)
    correct = models.BooleanField(_("to'g'ri"), default=False)
    answered_at = models.DateTimeField(_("vaqt"), auto_now_add=True)

    class Meta:
        verbose_name = _("javob")
        verbose_name_plural = _("javoblar")
        ordering = ("answered_at", "id")
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_quiz_answer")
        ]

    def __str__(self) -> str:
        return f"{self.attempt} · {self.question_id}"
