"""Kunlik statistika: raqamlar, voronka, 30 kunlik qator, muammolar va qo'ng'iroq ro'yxati.

Kun chegaralari Toshkent vaqti bo'yicha (`TIME_ZONE`). Xodimlar (`is_staff`) hisobga kirmaydi.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import CharField, Count, Exists, OuterRef, Q, QuerySet, Sum
from django.db.models.functions import Cast, TruncDate
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from apps.assistant.models import Conversation, Message
from apps.bot.models import BotChat
from apps.bot.subscription import problems as channel_problems
from apps.core.resources import disk_over_limit
from apps.exams import services as exams
from apps.homework.models import Submission
from apps.leads.models import Lead
from apps.learning.models import Enrollment, LessonProgress
from apps.live.models import Attendance
from apps.live.services import repeated_absences
from apps.notifications.models import Delivery, Notification
from apps.payments.models import Order, PaymentTransaction, Refund
from apps.quizzes.models import Attempt
from apps.users.models import OneTimeCode, SocialAccount, User
from apps.videos.models import VideoAsset

from .errors import error_counts

PERIODS = {
    "today": _("Bugun"),
    "yesterday": _("Kecha"),
    "7d": _("7 kun"),
    "30d": _("30 kun"),
}
PREVIOUS = {
    "today": _("kecha"),
    "yesterday": _("oldingi kun"),
    "7d": _("oldingi 7 kun"),
    "30d": _("oldingi 30 kun"),
}
UNANSWERED_AFTER = timedelta(hours=2)
# Uy vazifasi shuncha vaqt tekshirilmasa — muammo (TZ 4.8).
REVIEW_AFTER = timedelta(hours=48)
EXPIRED_WINDOW = timedelta(days=7)
AREA_TITLES = {
    "server": _("Server xatolari (500)"),
    "payments": _("To'lov modulida xatolar"),
    "messages": _("SMS va Telegram xatolari"),
    "auth": _("Kirish va ro'yxatdan o'tishda xatolar"),
    "ai": _("AI modulida xatolar"),
    "video": _("Video modulida xatolar"),
    "tasks": _("Fon vazifalarida xatolar"),
    "other": _("Boshqa xatolar"),
}


def day_start(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time.min))


@dataclass(frozen=True)
class Period:
    key: str
    start: datetime
    end: datetime

    @property
    def label(self) -> str:
        return str(PERIODS[self.key])

    @property
    def previous_label(self) -> str:
        return str(PREVIOUS[self.key])

    @property
    def previous(self) -> "Period":
        span = self.end - self.start
        return Period(self.key, self.start - span, self.start)

    @property
    def days(self) -> list[date]:
        first = timezone.localdate(self.start)
        count = (timezone.localdate(self.end - timedelta(seconds=1)) - first).days + 1
        return [first + timedelta(days=offset) for offset in range(count)]

    def range(self, field: str) -> dict[str, datetime]:
        return {f"{field}__gte": self.start, f"{field}__lt": self.end}


def period(key: str, now: datetime | None = None) -> Period:
    key = key if key in PERIODS else "today"
    today = timezone.localdate(now or timezone.now())
    tomorrow = day_start(today + timedelta(days=1))
    if key == "yesterday":
        return Period(key, day_start(today - timedelta(days=1)), day_start(today))
    if key == "7d":
        return Period(key, day_start(today - timedelta(days=6)), tomorrow)
    if key == "30d":
        return Period(key, day_start(today - timedelta(days=29)), tomorrow)
    return Period(key, day_start(today), tomorrow)


def students() -> QuerySet[User]:
    return User.objects.filter(is_staff=False)


@dataclass(frozen=True)
class Summary:
    registered: int
    kids: int
    via_telegram: int
    chose_course: int
    enrolled: int
    started_payment: int
    paid: int
    revenue: int
    leads: int
    leads_ai: int
    conversations: int
    ai_cost: Decimal


def summary(p: Period) -> Summary:
    joined = students().filter(**p.range("date_joined"))
    enrollments = Enrollment.objects.filter(**p.range("created_at"))
    orders = Order.objects.filter(**p.range("created_at"))
    paid = Order.objects.filter(status=Order.Status.PAID, **p.range("paid_at")).aggregate(
        count=Count("pk"), total=Sum("amount")
    )
    leads = Lead.objects.filter(**p.range("created_at"))
    ai_cost = Message.objects.filter(**p.range("created_at")).aggregate(total=Sum("cost_usd"))
    return Summary(
        registered=joined.count(),
        kids=joined.filter(audience=User.Audience.KIDS).count(),
        via_telegram=joined.filter(
            social_accounts__provider=SocialAccount.Provider.TELEGRAM
        ).count(),
        chose_course=students()
        .filter(Q(pk__in=enrollments.values("user_id")) | Q(pk__in=orders.values("user_id")))
        .count(),
        enrolled=enrollments.values("user_id").distinct().count(),
        started_payment=orders.values("user_id").distinct().count(),
        paid=paid["count"] or 0,
        revenue=paid["total"] or 0,
        leads=leads.count(),
        leads_ai=leads.exclude(source=Lead.Source.FORM).count(),
        conversations=Conversation.objects.filter(
            user_messages__gt=0, **p.range("created_at")
        ).count(),
        ai_cost=ai_cost["total"] or Decimal(0),
    )


@dataclass(frozen=True)
class Audience:
    """Bot va sayt foydalanuvchilari: jami (hozir) va davrda qo'shilganlar (`*_new`)."""

    bot: int
    bot_new: int
    bot_registered: int
    bot_blocked: int
    bot_muted: int
    students: int
    students_new: int
    telegram: int
    kids: int


def bot_joined(p: Period) -> int:
    """Davrda botga /start bosganlar."""
    return BotChat.objects.filter(**p.range("created_at")).count()


def audience(p: Period) -> Audience:
    chats = BotChat.objects.all()
    # Botdagi odam ro'yxatdan o'tgan: chat ID si biror akkauntning Telegram'i.
    linked = SocialAccount.objects.filter(
        provider=SocialAccount.Provider.TELEGRAM, uid=Cast(OuterRef("chat_id"), CharField())
    )
    people = students()
    return Audience(
        bot=chats.count(),
        bot_new=bot_joined(p),
        bot_registered=chats.filter(Exists(linked)).count(),
        bot_blocked=chats.filter(blocked_at__isnull=False).count(),
        bot_muted=chats.filter(news=False, blocked_at__isnull=True).count(),
        students=people.count(),
        students_new=people.filter(**p.range("date_joined")).count(),
        telegram=people.filter(
            Exists(
                SocialAccount.objects.filter(
                    user=OuterRef("pk"), provider=SocialAccount.Provider.TELEGRAM
                )
            )
        ).count(),
        kids=people.filter(audience=User.Audience.KIDS).count(),
    )


@dataclass(frozen=True)
class Learning:
    lessons: int
    quizzes: int
    learners: int
    homework: int


def learning(p: Period) -> Learning:
    """Davrda tugatilgan darslar, o'tilgan testlar, ulardan birini qilgan o'quvchilar va hozir
    tekshiruv kutayotgan uy vazifalari."""
    lessons = LessonProgress.objects.filter(user__is_staff=False, **p.range("completed_at"))
    quizzes = Attempt.objects.filter(passed=True, student__is_staff=False, **p.range("finished_at"))
    return Learning(
        lessons=lessons.count(),
        quizzes=quizzes.count(),
        learners=students()
        .filter(Q(pk__in=lessons.values("user_id")) | Q(pk__in=quizzes.values("student_id")))
        .count(),
        homework=Submission.objects.filter(status=Submission.Status.SUBMITTED).count(),
    )


@dataclass(frozen=True)
class Step:
    title: str
    count: int
    percent: int


def funnel(p: Period) -> list[Step]:
    """Shu davrda ro'yxatdan o'tganlar keyin nima qildi (hozirgacha)."""
    cohort = students().filter(**p.range("date_joined"))
    total = cohort.count()
    orders = Order.objects.filter(user=OuterRef("pk"))
    counts = [
        (_("Ro'yxatdan o'tdi"), total),
        (
            _("Kursga yozildi"),
            cohort.filter(Exists(Enrollment.objects.filter(user=OuterRef("pk")))).count(),
        ),
        (_("To'lovni boshladi"), cohort.filter(Exists(orders)).count()),
        (_("To'ladi"), cohort.filter(Exists(orders.filter(status=Order.Status.PAID))).count()),
    ]
    return [
        Step(str(title), count, round(count * 100 / total) if total else 0)
        for title, count in counts
    ]


def daily_series(days: int = 30, now: datetime | None = None) -> dict[str, list[Any]]:
    """Oxirgi `days` kun: har kungi ro'yxatdan o'tish va to'lovlar soni."""
    today = timezone.localdate(now or timezone.now())
    dates = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    start = day_start(dates[0])
    joined = dict(
        students()
        .filter(date_joined__gte=start)
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(count=Count("pk"))
        .values_list("day", "count")
    )
    paid = dict(
        Order.objects.filter(status=Order.Status.PAID, paid_at__gte=start)
        .annotate(day=TruncDate("paid_at"))
        .values("day")
        .annotate(count=Count("pk"))
        .values_list("day", "count")
    )
    return {
        "dates": dates,
        "registered": [joined.get(day, 0) for day in dates],
        "paid": [paid.get(day, 0) for day in dates],
    }


def admin_link(user: User | None, model: str, perm: str | None = None, **filters: str) -> str:
    """Admin ro'yxatiga havola — faqat ko'rish huquqi bo'lsa (aks holda 403 bo'lardi)."""
    app_label, model_name = model.split(".")
    if user is None or not user.has_perm(perm or f"{app_label}.view_{model_name}"):
        return ""
    url = reverse(f"admin:{app_label}_{model_name}_changelist")
    return f"{url}?{urlencode(filters)}" if filters else url


@dataclass(frozen=True)
class Problem:
    level: str  # danger | warning | info
    title: str
    count: int
    url: str = ""
    hint: str = ""


def problems(p: Period, viewer: User | None = None, now: datetime | None = None) -> list[Problem]:
    """Faqat bor muammolar: eng jiddiylari tepada. `viewer` — havolalar uning huquqiga qarab."""
    now = now or timezone.now()
    found: list[Problem] = []

    def add(level: str, title: object, count: int, url: str = "", hint: object = "") -> None:
        if count:
            found.append(Problem(level, str(title), count, url, str(hint)))

    add(
        "warning",
        _("2 soatdan beri javobsiz arizalar"),
        Lead.objects.filter(status=Lead.Status.NEW, created_at__lt=now - UNANSWERED_AFTER).count(),
        admin_link(viewer, "leads.lead", status__exact=Lead.Status.NEW),
    )
    add(
        "warning",
        _("Menejer kutayotgan AI suhbatlar"),
        Conversation.objects.filter(status=Conversation.Status.MANAGER).count(),
        admin_link(viewer, "assistant.conversation", status__exact=Conversation.Status.MANAGER),
    )
    ai_answers = Message.objects.filter(role=Message.Role.ASSISTANT, **p.range("created_at"))
    add(
        "danger",
        _("AI javob bera olmadi (xato)"),
        ai_answers.filter(model="fallback").count(),
        admin_link(viewer, "assistant.conversation"),
        _("Mijozga raqam qoldirish taklif qilindi. Sabab — server logi va Sentry'da."),
    )
    add(
        "warning",
        _("AI Claude'siz, oddiy rejimda javob berdi"),
        ai_answers.filter(model="rules").count(),
        admin_link(viewer, "assistant.assistantsettings"),
        _("Anthropic hisobidagi kredit, AI budjeti va AI yoqilganini tekshiring."),
    )
    codes = OneTimeCode.objects.filter(
        purpose=OneTimeCode.Purpose.REGISTER, **p.range("created_at")
    )
    lost = codes.filter(used_at__isnull=True, expires_at__lt=now).count()
    total_codes = codes.count()
    add(
        "warning" if lost >= 3 and lost * 2 >= total_codes else "info",
        _("SMS kod kiritilmadi"),
        lost,
        admin_link(viewer, "users.onetimecode"),
        _("%(lost)s / %(total)s kod: SMS yetib bormagan yoki odam ro'yxatdan o'tmay ketgan.")
        % {"lost": lost, "total": total_codes},
    )
    add(
        "info",
        _("To'lov oxiriga yetkazilmadi"),
        Order.objects.filter(
            status__in=[Order.Status.EXPIRED, Order.Status.CANCELLED], **p.range("created_at")
        ).count(),
        admin_link(viewer, "payments.order", status__exact=Order.Status.EXPIRED),
        _("Buyurtma ochildi, lekin 30 daqiqada to'lanmadi."),
    )
    add(
        "warning",
        _("Click to'lovi bekor bo'ldi"),
        PaymentTransaction.objects.filter(
            status=PaymentTransaction.Status.CANCELLED, **p.range("updated_at")
        ).count(),
        admin_link(
            viewer,
            "payments.paymenttransaction",
            status__exact=PaymentTransaction.Status.CANCELLED,
        ),
    )
    add(
        "warning",
        _("48 soatdan beri tekshirilmagan uy vazifalari"),
        Submission.objects.filter(
            status=Submission.Status.SUBMITTED, created_at__lt=now - REVIEW_AFTER
        ).count(),
        admin_link(viewer, "homework.submission", status__exact=Submission.Status.SUBMITTED),
    )
    add(
        "warning",
        _("Ketma-ket 2 marta darsga kelmagan o'quvchilar"),
        len(repeated_absences(now=now)),
        admin_link(viewer, "live.attendance", status__exact=Attendance.Status.ABSENT),
        _("O'qituvchi yoki menejer bog'lansin."),
    )
    add(
        "warning",
        _("Pul qaytarish so'rovlari"),
        Refund.objects.filter(status=Refund.Status.REQUESTED).count(),
        admin_link(viewer, "payments.refund", status__exact=Refund.Status.REQUESTED),
    )
    add(
        "danger",
        _("Video qayta ishlanmadi"),
        VideoAsset.objects.filter(status=VideoAsset.Status.FAILED).count(),
        admin_link(viewer, "videos.videoasset", status__exact=VideoAsset.Status.FAILED),
    )
    add(
        "warning",
        _("Xabar yetib bormadi (Telegram yoki SMS)"),
        Notification.objects.filter(**p.range("created_at"))
        .filter(Q(telegram=Delivery.FAILED) | Q(sms=Delivery.FAILED))
        .count(),
        admin_link(viewer, "notifications.notification", delivery="failed"),
    )
    add(
        "warning",
        _("Oylik imtihon tayyor emas"),
        exams.unready(now=now).count(),
        admin_link(viewer, "exams.exam", status__exact="DRAFT"),
        _("Ochilishiga 5 kundan kam qoldi: amaliy topshiriqlarni kiriting va «Tayyor» qiling."),
    )
    add(
        "warning",
        _("Baholanmagan imtihon topshiriqlari"),
        exams.pending_grading().filter(updated_at__lt=now - REVIEW_AFTER).count(),
        admin_link(viewer, "exams.exam"),
        _("48 soatdan beri: o'qituvchi kabinetda baholasin."),
    )
    add(
        "warning",
        _("Bot majburiy kanal a'zoligini tekshira olmayapti"),
        len(channel_problems()),
        admin_link(viewer, "bot.requiredchannel"),
        _("Botni kanalga administrator qiling — hozircha obuna so'ralmayapti."),
    )
    add(
        "danger",
        _("Server diski to'lmoqda (band, %)"),
        disk_over_limit(),
        hint=_("Eski videolarni o'chiring yoki diskni kengaytiring (AHOST paneli)."),
    )
    for area, count in error_counts(p.days).items():
        add("danger", AREA_TITLES[area], count, hint=_("Tafsilot — Sentry'da."))

    order = {"danger": 0, "warning": 1, "info": 2}
    return sorted(found, key=lambda item: order[item.level])


def without_course(p: Period, limit: int = 10) -> tuple[list[User], int]:
    """Davr ichida ro'yxatdan o'tib, hali kurs tanlamaganlar — menejer qo'ng'iroq qiladi."""
    users = (
        students()
        .filter(is_active=True, **p.range("date_joined"))
        .exclude(pk__in=Enrollment.objects.values("user_id"))
        .exclude(pk__in=Order.objects.values("user_id"))
        .order_by("-date_joined")
    )
    return list(users[:limit]), users.count()


def expired_access(now: datetime | None = None, limit: int = 10) -> tuple[list[Enrollment], int]:
    """Offlayn kurs: to'langan muddat oxirgi 7 kunda tugagan va hali yangilanmagan."""
    now = now or timezone.now()
    enrollments = (
        Enrollment.objects.filter(
            status=Enrollment.Status.ACTIVE,
            study_format=Enrollment.Format.OFFLINE,
            expires_at__gte=now - EXPIRED_WINDOW,
            expires_at__lt=now,
        )
        .select_related("user", "course")
        .order_by("-expires_at")
    )
    return list(enrollments[:limit]), enrollments.count()
