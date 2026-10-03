"""Daraja testi: boshlash, javob, natija, kupon va menejerga ariza; kupon eslatmalari.

Dvigatel — dars testlariniki (`Layout`, `grading`): savollar har urinishda tasodifiy tanlanadi,
variantlar urinish bo'yicha aralashtiriladi. Javob paytida to'g'ri/noto'g'ri aytilmaydi.
Kupon — birinchi tugatilgan testga, bir marta: yaxshi natijaga katta chegirma.
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.leads.models import Lead
from apps.leads.services import LeadInput, submit_lead
from apps.learning.models import Enrollment
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import day_month, locale_of, text
from apps.payments.models import Order
from apps.quizzes import grading
from apps.quizzes.models import Question
from apps.quizzes.services import Layout, load_questions
from apps.rewards import services as rewards
from apps.rewards.models import Coupon
from apps.users.models import User

from .models import PlacementAnswer, PlacementAttempt, PlacementTest

FIRST_REMINDER = timedelta(hours=24)
LAST_REMINDER = timedelta(hours=12)


class PlacementError(ValueError):
    pass


@dataclass(frozen=True)
class Outcome:
    attempt: PlacementAttempt
    level: str  # beginner | middle | good
    coupon: Coupon | None


def active_tests() -> list[PlacementTest]:
    """Botda ko'rsatiladigan testlar: faol va savoli bor."""
    return list(
        PlacementTest.objects.filter(is_active=True, quiz__questions__isnull=False)
        .select_related("course")
        .distinct()
        .order_by("order", "id")
    )


def is_newcomer(user: Any) -> bool:
    """Hali hech qaysi kursga yozilmagan (faol yozilishi yo'q) o'quvchi."""
    if user is None or user.is_staff or user.is_superuser:
        return False
    return not Enrollment.objects.filter(user_id=user.pk, status=Enrollment.Status.ACTIVE).exists()


def eligible(user: Any) -> bool:
    """Daraja testi va kupon kimga: hali kursga yozilmagan o'quvchi; bosh admin — sinab ko'rish
    uchun. Kursda o'qiyotganlar kupon olib, keyingi oy to'loviga ishlatmasin."""
    if user is None or not user.is_active:
        return False
    return bool(user.is_superuser) or is_newcomer(user)


def level_of(score: int) -> str:
    good = rewards.settings().placement_good_percent
    if score >= good:
        return "good"
    return "middle" if score >= 40 else "beginner"


# --- Test ---


def current(attempt: PlacementAttempt) -> tuple[int, int, Question] | None:
    """Birinchi javobsiz savol: (tartib raqami, jami, savol). Hammasi javoblangan — None."""
    questions = load_questions(attempt.question_ids)
    ids = [question_id for question_id in attempt.question_ids if question_id in questions]
    answered = set(attempt.answers.values_list("question_id", flat=True))
    for index, question_id in enumerate(ids, 1):
        if question_id not in answered:
            return index, len(ids), questions[question_id]
    return None


def seconds_left(attempt: PlacementAttempt, *, now: datetime | None = None) -> int:
    if attempt.finished_at is not None:
        return 0
    return max(0, int((attempt.deadline - (now or timezone.now())).total_seconds()))


def start(test: PlacementTest, user: User, *, now: datetime | None = None) -> PlacementAttempt:
    """Yangi urinish yoki vaqti tugamagan tugallanmaganini davom ettirish. Qayta ishlash mumkin
    (kupon faqat birinchi tugatilganiga)."""
    now = now or timezone.now()
    if not test.is_active:
        raise PlacementError(_("Bu test hozir mavjud emas."))
    if not eligible(user):
        raise PlacementError(_("Daraja testi — hali kursga yozilmaganlar uchun."))
    running = PlacementAttempt.objects.filter(test=test, user=user, finished_at__isnull=True)
    for attempt in running:
        if attempt.deadline > now:
            return attempt
        finish(attempt, now=now)
    pool = list(Question.objects.filter(quiz_id=test.quiz_id).values_list("pk", flat=True))
    if not pool:
        raise PlacementError(_("Bu testda hali savol yo'q."))
    rng = random.SystemRandom()
    ids = rng.sample(pool, min(test.questions_count, len(pool)))
    return PlacementAttempt.objects.create(
        test=test,
        user=user,
        question_ids=ids,
        seed=rng.randrange(1, 2**31),
        deadline=now + timedelta(minutes=test.duration_min),
    )


def answer(
    attempt: PlacementAttempt,
    question_id: int,
    response: dict[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    now = now or timezone.now()
    if attempt.finished_at is not None:
        raise PlacementError(_("Test yakunlangan."))
    if now >= attempt.deadline:
        raise PlacementError(_("Vaqt tugadi — berilgan javoblaringiz saqlandi."))
    if question_id not in attempt.question_ids:
        raise PlacementError(_("Bu savol ushbu testda yo'q."))
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if question is None:
        raise PlacementError(_("Savol topilmadi."))
    layout = Layout.build(question, attempt.seed)
    private = layout.to_private(response)
    if private is None:
        raise PlacementError(_("Javob formati noto'g'ri."))
    try:
        with transaction.atomic():
            PlacementAnswer.objects.create(
                attempt=attempt,
                question=question,
                response=private,
                correct=grading.grade(question, layout.choices, private),
            )
    except IntegrityError as exc:
        raise PlacementError(_("Bu savolga javob berilgan.")) from exc


def finish(attempt: PlacementAttempt, *, now: datetime | None = None) -> Outcome:
    """Natija (javobsiz savollar noto'g'ri) va ariza. Kupon — birinchi tugatilgan testga (hali
    kursga yozilmagan bo'lsa)."""
    now = now or timezone.now()
    with transaction.atomic():
        locked = PlacementAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked.finished_at is not None:
            return Outcome(locked, level_of(locked.score or 0), locked.coupon)
        total = len(locked.question_ids)
        correct = locked.answers.filter(correct=True).count()
        locked.score = round(correct * 100 / total) if total else 0
        locked.finished_at = min(now, locked.deadline)
        user = User.objects.select_for_update().get(pk=locked.user_id)
        first = (
            eligible(user)
            and not Coupon.objects.filter(user=user, kind=Coupon.Kind.PLACEMENT).exists()
        )
        coupon = issue_coupon(user, locked.score, now=now) if first else None
        locked.coupon = coupon
        locked.save(update_fields=["score", "finished_at", "coupon"])
    test = PlacementTest.objects.select_related("course").get(pk=locked.test_id)
    transaction.on_commit(lambda: send_lead(user, test, locked, coupon))
    attempt.score, attempt.finished_at, attempt.coupon = locked.score, locked.finished_at, coupon
    return Outcome(locked, level_of(locked.score), coupon)


def issue_coupon(user: User, score: int, *, now: datetime) -> Coupon:
    config = rewards.settings()
    good = score >= config.placement_good_percent
    return Coupon.objects.create(
        user=user,
        percent=config.placement_high_coupon if good else config.placement_low_coupon,
        kind=Coupon.Kind.PLACEMENT,
        expires_at=now + timedelta(hours=config.placement_coupon_hours),
    )


def send_lead(
    user: User, test: PlacementTest, attempt: PlacementAttempt, coupon: Coupon | None
) -> None:
    """Menejerga ariza: kim, qaysi yo'nalish, natija va kupon — qo'ng'iroq uchun."""
    note = f"Daraja testi ({test.title}): {attempt.score}%"
    if coupon is not None and coupon.expires_at is not None:
        until = timezone.localtime(coupon.expires_at)
        note += f", kupon {coupon.percent}% ({until:%d.%m %H:%M} gacha)"
    if user.signup_source:
        note += f", manba: {user.signup_source}"
    submit_lead(
        LeadInput(
            name=user.get_full_name() or user.first_name or user.phone,
            phone=user.phone,
            course=test.course,
            comment=note,
            locale=user.locale or "uz",
            source=Lead.Source.BOT_TEST,
            utm={"utm_source": user.signup_source} if user.signup_source else {},
        )
    )


def close_expired(*, now: datetime | None = None) -> int:
    """Vaqti tugagan, lekin yakunlanmagan testlar (odam botga qaytmadi): natija, kupon va ariza
    yo'qolmaydi. Kupon berilgan bo'lsa — xabar (Telegram'ga ham)."""
    now = now or timezone.now()
    expired = PlacementAttempt.objects.filter(
        finished_at__isnull=True, deadline__lt=now
    ).select_related("user")
    closed = 0
    for attempt in expired:
        outcome = finish(attempt, now=now)
        closed += 1
        coupon = outcome.coupon
        if coupon is None or coupon.expires_at is None:
            continue
        user = attempt.user
        locale = locale_of(user.locale)
        until = timezone.localtime(coupon.expires_at)
        with translation.override(locale):
            notify(
                user,
                Notification.Kind.COUPON,
                title=text(locale, "placement_timeout_title", score=str(outcome.attempt.score)),
                body=text(
                    locale,
                    "placement_timeout_body",
                    percent=str(coupon.percent),
                    until=f"{day_month(until.date(), locale)}, {until:%H:%M}",
                ),
                link="/dashboard/rewards",
                dedupe_key=f"placement-closed:{attempt.pk}",
            )
    return closed


# --- Kupon eslatmalari ---


def coupon_reminders(*, now: datetime | None = None) -> int:
    """Daraja testi kuponi: 24 soatdan keyin va muddat tugashiga 12 soat qolganda. Kupon
    ishlatilgan yoki o'quvchi kursga yozilgan bo'lsa — yuborilmaydi (to'lovni boshlab, oxiriga
    yetkazmaganga — yuboriladi)."""
    now = now or timezone.now()
    coupons = (
        Coupon.objects.filter(kind=Coupon.Kind.PLACEMENT, used_at__isnull=True, expires_at__gt=now)
        .exclude(order__status=Order.Status.PAID)
        .select_related("user")
    )
    sent = 0
    for coupon in coupons:
        user = coupon.user
        if not user.is_active or not is_newcomer(user) or coupon.expires_at is None:
            continue
        if coupon.expires_at - now <= LAST_REMINDER:
            key, title_key = f"coupon-last:{coupon.pk}", "coupon_last_title"
        elif now - coupon.created_at >= FIRST_REMINDER:
            key, title_key = f"coupon-first:{coupon.pk}", "coupon_first_title"
        else:
            continue
        locale = locale_of(user.locale)
        until = timezone.localtime(coupon.expires_at)
        with translation.override(locale):
            created = notify(
                user,
                Notification.Kind.COUPON,
                title=text(locale, title_key, percent=str(coupon.percent)),
                body=text(
                    locale,
                    "coupon_body",
                    percent=str(coupon.percent),
                    until=f"{day_month(until.date(), locale)}, {until:%H:%M}",
                ),
                link="/dashboard/rewards",
                dedupe_key=key,
            )
        sent += created is not None
    return sent
