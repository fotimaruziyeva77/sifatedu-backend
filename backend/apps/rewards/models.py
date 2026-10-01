"""XP, coin, kunlik topshiriqlar, shtraflar va referal kuponlari.

Ikki valyuta: **XP** — reyting uchun, sarflanmaydi; shtraflar faqat XP'dan (0 dan pastga
tushmaydi). **Coin** — do'kon uchun: har topilgan XP bilan teng coin, referal mukofotlari ham
coinda. Har o'zgarish — `Entry` (sababi bilan); bir harakat — bir marta (`key`).
"""

from django.conf import settings
from django.core.cache import cache
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

SETTINGS_CACHE_KEY = "rewards:settings"


class GameSettings(models.Model):
    """Qiymatlar (bitta yozuv): admin'da o'zgartiriladi."""

    lesson_xp = models.PositiveSmallIntegerField(_("dars tugatildi (XP)"), default=10)
    quiz_xp = models.PositiveSmallIntegerField(
        _("dars testidan birinchi marta o'tildi (XP)"), default=15
    )
    homework_xp = models.PositiveSmallIntegerField(_("uy vazifasi topshirildi (XP)"), default=20)
    attendance_xp = models.PositiveSmallIntegerField(_("darsga vaqtida kelindi (XP)"), default=10)
    exam_xp = models.PositiveSmallIntegerField(_("oylik imtihondan o'tildi (XP)"), default=50)
    daily_bonus_xp = models.PositiveSmallIntegerField(
        _("kunlik topshiriqlar bajarildi — bonus (XP)"), default=10
    )
    daily_missed_penalty = models.PositiveSmallIntegerField(
        _("kunlik topshiriqlar bajarilmadi (−XP)"), default=5
    )
    absent_penalty = models.PositiveSmallIntegerField(
        _("darsga sababsiz kelmadi (−XP)"), default=15
    )
    late_penalty = models.PositiveSmallIntegerField(_("darsga kechikdi (−XP)"), default=5)
    homework_late_penalty = models.PositiveSmallIntegerField(
        _("uy vazifasi muddatidan kechikdi (−XP)"), default=10
    )
    referral_lesson_coins = models.PositiveSmallIntegerField(
        _("do'st birinchi darsni tugatdi (coin)"), default=50
    )
    referral_paid_coins = models.PositiveSmallIntegerField(
        _("do'st to'lov qildi (coin)"), default=100
    )
    referral_discount = models.PositiveSmallIntegerField(
        _("do'stning birinchi to'loviga chegirma (%)"),
        default=10,
        validators=[MaxValueValidator(90)],
    )
    coupon_percent = models.PositiveSmallIntegerField(
        _("taklif qilganga kupon (%)"), default=10, validators=[MaxValueValidator(90)]
    )
    daily_tasks = models.BooleanField(
        _("kunlik topshiriqlar"),
        default=True,
        help_text=_("Har kuni 09:00 da har bir faol o'quvchiga 3 ta topshiriq."),
    )
    announce_winners = models.BooleanField(
        _("haftalik g'oliblarni kanalga e'lon qilish"),
        default=False,
        help_text=_("Dushanba 10:00 da o'tgan haftaning eng yaxshi 3 o'quvchisi majburiy kanalga."),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("XP va coin sozlamalari")
        verbose_name_plural = _("XP va coin sozlamalari")

    def __str__(self) -> str:
        return str(_("XP va coin sozlamalari"))

    def save(self, *args: object, **kwargs: object) -> None:
        self.pk = 1
        super().save(*args, **kwargs)  # type: ignore[arg-type]
        cache.delete(SETTINGS_CACHE_KEY)

    @classmethod
    def load(cls) -> "GameSettings":
        found: GameSettings | None = cache.get(SETTINGS_CACHE_KEY)
        if found is None:
            found, _created = cls.objects.get_or_create(pk=1)
            cache.set(SETTINGS_CACHE_KEY, found, 300)
        return found


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="wallet",
    )
    xp = models.PositiveIntegerField(_("XP"), default=0)
    coins = models.PositiveIntegerField(_("coin"), default=0)
    streak = models.PositiveSmallIntegerField(_("seriya (kun)"), default=0)
    best_streak = models.PositiveSmallIntegerField(_("eng uzun seriya"), default=0)
    streak_day = models.DateField(_("oxirgi to'liq kun"), null=True, blank=True)
    hidden = models.BooleanField(
        _("reytingda ko'rsatilmasin"),
        default=False,
        help_text=_("O'quvchi sozlamalarda o'zi yoqadi."),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("hamyon")
        verbose_name_plural = _("hamyonlar")

    def __str__(self) -> str:
        return f"{self.user} · {self.xp} XP · {self.coins} coin"


class Entry(models.Model):
    """XP va coin o'zgarishi. Shtrafni o'qituvchi yoki admin bekor qiladi (sabab bilan)."""

    class Reason(models.TextChoices):
        LESSON = "LESSON", _("Dars tugatildi")
        QUIZ = "QUIZ", _("Dars testidan o'tildi")
        HOMEWORK = "HOMEWORK", _("Uy vazifasi topshirildi")
        ATTENDANCE = "ATTENDANCE", _("Darsga vaqtida kelindi")
        EXAM = "EXAM", _("Oylik imtihondan o'tildi")
        DAILY = "DAILY", _("Kunlik topshiriqlar bajarildi")
        DAILY_MISSED = "DAILY_MISSED", _("Kunlik topshiriqlar bajarilmadi")
        ABSENT = "ABSENT", _("Darsga sababsiz kelmadi")
        LATE = "LATE", _("Darsga kechikdi")
        HOMEWORK_LATE = "HOMEWORK_LATE", _("Uy vazifasi muddatidan kechikdi")
        REFERRAL = "REFERRAL", _("Do'st birinchi darsni tugatdi")
        REFERRAL_PAID = "REFERRAL_PAID", _("Do'st to'lov qildi")
        PURCHASE = "PURCHASE", _("Do'kondan sovg'a")
        REFUND = "REFUND", _("Sovg'a bekor qilindi")
        MANUAL = "MANUAL", _("Qo'lda")

    PENALTIES = (Reason.DAILY_MISSED, Reason.ABSENT, Reason.LATE, Reason.HOMEWORK_LATE)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="reward_entries",
    )
    reason = models.CharField(_("sabab"), max_length=20, choices=Reason.choices, db_index=True)
    xp = models.IntegerField(_("XP"), default=0)
    # Shtraf XP'ni 0 dan pastga tushirmaydi: aslida yechilgani (bekor qilinganda shu qaytadi).
    applied_xp = models.IntegerField(_("hisoblangan XP"), default=0, editable=False)
    coins = models.IntegerField(_("coin"), default=0)
    key = models.CharField(max_length=100, editable=False)
    course = models.ForeignKey(
        "catalog.Course",
        verbose_name=_("kurs"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    note = models.CharField(_("izoh"), max_length=200, blank=True)
    created_at = models.DateTimeField(_("vaqt"), auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("kim qo'shdi"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    canceled_at = models.DateTimeField(_("bekor qilingan"), null=True, blank=True)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("kim bekor qildi"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    cancel_reason = models.CharField(_("bekor qilish sababi"), max_length=300, blank=True)

    class Meta:
        verbose_name = _("XP va coin tarixi")
        verbose_name_plural = _("XP va coin tarixi")
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=["key"],
                condition=Q(canceled_at__isnull=True),
                name="unique_active_reward_key",
            )
        ]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self) -> str:
        return f"{self.user} · {self.get_reason_display()}"

    @property
    def is_penalty(self) -> bool:
        return self.reason in self.PENALTIES


class DailyTask(models.Model):
    class Kind(models.TextChoices):
        LESSON = "LESSON", _("Keyingi darsni ko'rish")
        QUIZ = "QUIZ", _("Dars testidan o'tish")
        REVIEW = "REVIEW", _("Botda takrorlash (5 savol)")
        HOMEWORK = "HOMEWORK", _("Uy vazifasini topshirish")
        LIVE = "LIVE", _("Bugungi darsga vaqtida kelish")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="daily_tasks",
    )
    day = models.DateField(_("kun"), default=timezone.localdate, db_index=True)
    kind = models.CharField(_("topshiriq"), max_length=10, choices=Kind.choices)
    course = models.ForeignKey(
        "catalog.Course", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    lesson = models.ForeignKey(
        "catalog.Lesson", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    quiz = models.ForeignKey(
        "quizzes.Quiz", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    assignment = models.ForeignKey(
        "homework.Assignment", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    live_lesson = models.ForeignKey(
        "live.LiveLesson", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    title = models.CharField(_("nima"), max_length=300, blank=True)
    done_at = models.DateTimeField(_("bajarildi"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("kunlik topshiriq")
        verbose_name_plural = _("kunlik topshiriqlar")
        ordering = ("-day", "pk")
        constraints = [
            models.UniqueConstraint(fields=["user", "day", "kind"], name="unique_daily_task")
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.day} · {self.get_kind_display()}"


class ReviewAttempt(models.Model):
    """Botda takrorlash: o'tilgan testlardan 5 savol (har javobdan keyin ✅/❌)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_attempts"
    )
    question_ids = models.JSONField(default=list)
    seed = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=dict)
    correct = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("takrorlash")
        verbose_name_plural = _("takrorlashlar")

    def __str__(self) -> str:
        return f"{self.user} · {self.started_at:%Y-%m-%d}"


class Coupon(models.Model):
    """Chegirma kuponi (taklif qilganga, do'st to'lagach). Bitta to'lovga bitta."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("egasi"),
        on_delete=models.CASCADE,
        related_name="coupons",
    )
    percent = models.PositiveSmallIntegerField(_("chegirma (%)"))
    friend = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("kim sababli"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # Buyurtmaga biriktirilgan (to'lov kutilmoqda) yoki ishlatilgan.
    order = models.ForeignKey(
        "payments.Order",
        verbose_name=_("buyurtma"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coupons",
    )
    used_at = models.DateTimeField(_("ishlatilgan"), null=True, blank=True)
    created_at = models.DateTimeField(_("berilgan"), auto_now_add=True)

    class Meta:
        verbose_name = _("kupon")
        verbose_name_plural = _("kuponlar")
        ordering = ("created_at", "pk")

    def __str__(self) -> str:
        return f"{self.user} · {self.percent}%"
