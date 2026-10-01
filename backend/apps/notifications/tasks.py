import logging
from datetime import timedelta
from typing import Any

from celery import Task, shared_task
from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone, translation

from . import services, telegram
from .models import Broadcast, Delivery, Notification
from .sms import SmsNotConfiguredError, send_sms
from .texts import day_month, locale_of, text

logger = logging.getLogger(__name__)

DELIVERY_RETRIES = 5
EXPIRING_DAYS = 3


@shared_task(
    autoretry_for=(OSError, RuntimeError),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def send_sms_task(phone: str, text: str) -> None:
    """SMS navbat orqali yuboriladi: provayder vaqtincha ishlamasa, qayta uriniladi."""
    try:
        send_sms(phone, text)
    except SmsNotConfiguredError:
        # Production'da bu xato — foydalanuvchi kodni olmaydi (Sentry'ga ham tushadi).
        logger.error("SMS sozlanmagan: ESKIZ_EMAIL/ESKIZ_PASSWORD yo'q, SMS yuborilmadi")


@shared_task(
    autoretry_for=(OSError, RuntimeError),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def send_alert_task(text: str) -> None:
    """Jamoa chatiga ogohlantirish (apps/notifications/alerts.py)."""
    try:
        telegram.send_message(settings.TELEGRAM_ALERTS_CHAT_ID, text)
    except telegram.TelegramNotConfiguredError:
        logger.warning("Ogohlantirish yuborilmadi: Telegram sozlanmagan")


# `bulk` navbati: soniyasiga bitta to'plam (25 ta xabar) — Telegram limiti 30 xabar/soniya.
@shared_task(bind=True, rate_limit="1/s", max_retries=DELIVERY_RETRIES)
def deliver(self: Task, notification_ids: list[int]) -> str:
    """Xabarlarni Telegram va SMS orqali yetkazadi. Qayta urinishda faqat qolganlari ketadi."""
    pending = list(
        Notification.objects.filter(pk__in=notification_ids)
        .filter(Q(telegram=Delivery.QUEUED) | Q(sms=Delivery.QUEUED))
        .select_related("user")
        .order_by("pk")
    )
    accounts = services.telegram_accounts(item.user_id for item in pending)
    for notification in pending:
        try:
            services.deliver_one(notification, accounts.get(notification.user_id))
        except telegram.TelegramError as exc:
            # 429: Telegram aytgan vaqtcha kutamiz.
            raise self.retry(countdown=exc.retry_after or 5, exc=exc) from exc
        except OSError as exc:
            if self.request.retries >= DELIVERY_RETRIES:
                _give_up(notification_ids, "tarmoq xatosi")
                logger.error("Xabarlar yetkazilmadi (tarmoq): %s", exc)
                return "failed"
            raise self.retry(countdown=5 * 2**self.request.retries, exc=exc) from exc
    return f"{len(pending)}"


def _give_up(notification_ids: list[int], reason: str) -> None:
    base = Notification.objects.filter(pk__in=notification_ids)
    base.filter(telegram=Delivery.QUEUED).update(telegram=Delivery.FAILED, error=reason)
    base.filter(sms=Delivery.QUEUED).update(sms=Delivery.FAILED, error=reason)


@shared_task
def send_broadcast(broadcast_id: int) -> str:
    return f"{services.send(broadcast_id)}"


@shared_task
def send_scheduled_broadcasts() -> str:
    """Ertalabga surilgan aksiyalar (tungi vaqtda "Yuborish" bosilgan)."""
    due = Broadcast.objects.filter(
        status=Broadcast.Status.SCHEDULED, scheduled_for__lte=timezone.now()
    ).values_list("pk", flat=True)
    sent = [services.send(pk) for pk in due]
    return f"{len([count for count in sent if count])}"


@shared_task
def remind_expiring() -> str:
    """Offlayn kurs: to'langan muddat 3 kun ichida tugaydi yoki tugadi. Har biri bir marta."""
    from apps.learning.models import Enrollment

    now = timezone.now()
    horizon = services.day_start(timezone.localdate(now) + timedelta(days=EXPIRING_DAYS + 1))
    enrollments = Enrollment.objects.filter(
        status=Enrollment.Status.ACTIVE,
        study_format=Enrollment.Format.OFFLINE,
        expires_at__gt=now - timedelta(days=2),
        expires_at__lt=horizon,
    ).select_related("user", "course")
    sent = 0
    for enrollment in enrollments:
        user = enrollment.user
        if enrollment.expires_at is None or not user.is_active:
            continue
        locale = locale_of(user.locale)
        ends = timezone.localdate(enrollment.expires_at)
        expired = enrollment.expires_at <= now
        with translation.override(locale):
            course = str(enrollment.course.title)
        kind = Notification.Kind.ACCESS_EXPIRED if expired else Notification.Kind.ACCESS_EXPIRING
        key = "expired" if expired else "expiring"
        created = services.notify(
            user,
            kind,
            title=text(locale, f"{key}_title"),
            body=text(locale, f"{key}_body", course=course, date=day_month(ends, locale)),
            link=f"/dashboard/catalog/{enrollment.course.slug}",
            dedupe_key=f"{key}:{enrollment.pk}:{ends.isoformat()}",
        )
        sent += created is not None
    return f"{sent}"


# Katta muddat birinchi: 8 kundan beri o'qimagan o'quvchiga faqat 7 kunlik eslatma boradi.
# (kun, gacha): 3–6 kun — birinchi eslatma, 7–13 — ikkinchisi. Ikki haftadan keyin yozmaymiz:
# matn aniq qolsin va uzoq ketgan o'quvchi bezovta qilinmasin.
INACTIVE_STEPS = ((7, 14), (3, 7))


def last_activity(user_ids: set[int], course_ids: set[int]) -> dict[tuple[int, int], Any]:
    """(o'quvchi, kurs) → oxirgi faollik: dars ko'rish, vazifa yuborish yoki test."""
    from apps.homework.models import Submission
    from apps.learning.models import LessonProgress
    from apps.quizzes.models import Attempt

    sources = [
        LessonProgress.objects.filter(
            user_id__in=user_ids, lesson__module__course_id__in=course_ids
        )
        .values("user_id", "lesson__module__course_id")
        .annotate(moment=Max("updated_at"))
        .values_list("user_id", "lesson__module__course_id", "moment"),
        Submission.objects.filter(
            student_id__in=user_ids, assignment__lesson__module__course_id__in=course_ids
        )
        .values("student_id", "assignment__lesson__module__course_id")
        .annotate(moment=Max("created_at"))
        .values_list("student_id", "assignment__lesson__module__course_id", "moment"),
        Attempt.objects.filter(
            student_id__in=user_ids, quiz__lesson__module__course_id__in=course_ids
        )
        .values("student_id", "quiz__lesson__module__course_id")
        .annotate(moment=Max("started_at"))
        .values_list("student_id", "quiz__lesson__module__course_id", "moment"),
    ]
    latest: dict[tuple[int, int], Any] = {}
    for rows in sources:
        for user_id, course_id, moment in rows:
            key = (user_id, course_id)
            if moment is not None and (key not in latest or moment > latest[key]):
                latest[key] = moment
    return latest


@shared_task
def remind_inactive() -> str:
    """Kursni boshlagan, lekin 3 va 7 kundan beri o'qimagan o'quvchiga keyingi dars havolasi.
    Har bir tanaffus uchun har bosqich bir marta; kursni boshlamagan va tugatganlarga yo'q."""
    from apps.catalog.models import Lesson
    from apps.learning.models import Enrollment, LessonProgress

    enrollments = [
        enrollment
        for enrollment in Enrollment.objects.filter(
            status=Enrollment.Status.ACTIVE, user__is_active=True, user__is_staff=False
        ).select_related("user", "course")
        if enrollment.is_open
    ]
    if not enrollments:
        return "0"
    user_ids = {enrollment.user_id for enrollment in enrollments}
    course_ids = {enrollment.course_id for enrollment in enrollments}
    latest = last_activity(user_ids, course_ids)
    done = set(
        LessonProgress.objects.filter(user_id__in=user_ids, completed_at__isnull=False).values_list(
            "user_id", "lesson_id"
        )
    )
    program: dict[int, list[Any]] = {}
    for lesson in (
        Lesson.objects.filter(module__course_id__in=course_ids)
        .select_related("module")
        .order_by("module__order", "module__id", "order", "id")
    ):
        program.setdefault(lesson.module.course_id, []).append(lesson)

    today = timezone.localdate()
    sent = 0
    for enrollment in enrollments:
        moment = latest.get((enrollment.user_id, enrollment.course_id))
        if moment is None:
            continue
        last_day = timezone.localdate(moment)
        idle = (today - last_day).days
        step = next((days for days, until in INACTIVE_STEPS if days <= idle < until), None)
        upcoming = next(
            (
                lesson
                for lesson in program.get(enrollment.course_id, [])
                if (enrollment.user_id, lesson.pk) not in done
            ),
            None,
        )
        if step is None or upcoming is None:
            continue
        user = enrollment.user
        locale = locale_of(user.locale)
        with translation.override(locale):
            course = str(enrollment.course.title)
            lesson_title = str(upcoming.title)
        created = services.notify(
            user,
            Notification.Kind.INACTIVE,
            title=text(locale, f"inactive_{step}_title"),
            body=text(locale, f"inactive_{step}_body", course=course, lesson=lesson_title),
            link=f"/dashboard/courses/{enrollment.course.slug}/lessons/{upcoming.pk}",
            dedupe_key=f"inactive:{enrollment.pk}:{last_day.isoformat()}:{step}",
        )
        sent += created is not None
    return f"{sent}"
