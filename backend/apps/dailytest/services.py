"""Kunlik test: ochish (07:00), eslatma (20:00), yopish (23:00), ishlash va reyting.

Savollar banki — guruhda «Dars o'tildi» deb belgilangan darslar testlari. Har o'quvchiga o'zicha
tasodifiy savollar (kechagilari iloji boricha takrorlanmaydi), variantlar urinish bo'yicha
aralashtiriladi (`Layout`). Bank kerakli sondan kichik bo'lsa — test berilmaydi va o'qituvchiga
haftada bir eslatma boradi.
"""

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import QuerySet, Sum
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.learning.models import StudyGroup
from apps.live.models import GroupLesson
from apps.live.services import members, student_group_ids
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import locale_of, text
from apps.quizzes import grading
from apps.quizzes.models import Question
from apps.quizzes.services import Layout, load_questions
from apps.rewards import services as rewards
from apps.rewards.models import Entry
from apps.rewards.rating import short_name
from apps.users.models import User

from .models import DailyAnswer, DailyAttempt, DailyTest

OPEN_AT = time(7, 0)
CLOSE_AT = time(23, 0)
LINK = "/dashboard/daily-test"
TOP = 10


class DailyTestError(ValueError):
    pass


@dataclass(frozen=True)
class Result:
    attempt: DailyAttempt
    xp: int
    coins: int
    place: int
    people: int

    @property
    def correct(self) -> int:
        return self.attempt.correct

    @property
    def wrong(self) -> int:
        return self.attempt.total - self.attempt.correct


@dataclass(frozen=True)
class Row:
    student_id: int
    name: str
    correct: int
    total: int


# --- Vaqt ---


def local_day(now: datetime | None = None) -> date:
    return timezone.localtime(now or timezone.now()).date()


def window(day: date) -> tuple[datetime, datetime]:
    return (
        timezone.make_aware(datetime.combine(day, OPEN_AT)),
        timezone.make_aware(datetime.combine(day, CLOSE_AT)),
    )


def is_open(test: DailyTest, now: datetime | None = None) -> bool:
    now = now or timezone.now()
    return test.status == DailyTest.Status.OPEN and test.opens_at <= now < test.closes_at


# --- Savollar ---


def pool(group: StudyGroup) -> list[int]:
    """O'tilgan darslar testlaridagi savollar."""
    covered = GroupLesson.objects.filter(group=group).values("lesson_id")
    return list(
        Question.objects.filter(quiz__lesson_id__in=covered)
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def choose(test: DailyTest, student: User) -> list[int]:
    """Tasodifiy savollar: kechagi testdagilar iloji boricha qaytarilmaydi."""
    bank = pool(test.group)
    count = min(test.questions_count, len(bank))
    yesterday = {
        question_id
        for ids in DailyAttempt.objects.filter(
            student=student, test__day=test.day - timedelta(days=1)
        ).values_list("question_ids", flat=True)
        for question_id in ids
    }
    rng = random.SystemRandom()
    fresh = [question_id for question_id in bank if question_id not in yesterday]
    if len(fresh) >= count:
        chosen = rng.sample(fresh, count)
    else:
        rest = [question_id for question_id in bank if question_id in yesterday]
        chosen = fresh + rng.sample(rest, count - len(fresh))
        rng.shuffle(chosen)
    return chosen


# --- Ochish, eslatma, yopish (fon vazifalari) ---


def open_day(*, now: datetime | None = None) -> int:
    """07:00: har o'qiyotgan guruhga bugungi test va o'quvchilarga xabar. Savol yetmasa — test
    berilmaydi, o'qituvchiga eslatma. Qaytaradi: ochilgan testlar soni."""
    now = now or timezone.now()
    config = rewards.settings()
    if not config.daily_test:
        return 0
    day = local_day(now)
    opens_at, closes_at = window(day)
    opened = 0
    groups = StudyGroup.objects.filter(status=StudyGroup.Status.ACTIVE).select_related(
        "course", "teacher"
    )
    for group in groups:
        students = list(members(group.pk, now=now))
        if not students:
            continue
        test, created = DailyTest.objects.get_or_create(
            group=group,
            day=day,
            defaults={
                "questions_count": config.daily_test_questions,
                "opens_at": opens_at,
                "closes_at": closes_at,
            },
        )
        if not created:
            continue
        test.pool_size = len(pool(group))
        if test.pool_size < test.questions_count:
            test.status = DailyTest.Status.SKIPPED
            test.save(update_fields=["pool_size", "status", "updated_at"])
            warn_teacher(test)
            continue
        test.save(update_fields=["pool_size", "updated_at"])
        for student in students:
            announce(test, student)
        opened += 1
    return opened


def announce(test: DailyTest, student: User) -> Notification | None:
    locale = locale_of(student.locale)
    body = text(locale, "daily_test_body", count=str(test.questions_count))
    previous = (
        DailyAttempt.objects.filter(
            student=student,
            test__group=test.group,
            test__day=test.day - timedelta(days=1),
            finished_at__isnull=False,
        )
        .select_related("test")
        .first()
    )
    if previous is not None:
        rows = day_rating(previous.test)
        place = next(
            (index for index, row in enumerate(rows, 1) if row.student_id == student.pk), 0
        )
        body += "\n" + text(
            locale,
            "daily_test_yesterday",
            correct=str(previous.correct),
            total=str(previous.total),
            place=str(place),
            people=str(len(rows)),
        )
    with translation.override(locale):
        return notify(
            student,
            Notification.Kind.DAILY_TEST,
            title=text(locale, "daily_test_title"),
            body=body,
            link=LINK,
            dedupe_key=f"daily-test:{test.pk}:{student.pk}",
        )


def warn_teacher(test: DailyTest) -> Notification | None:
    """Savollar yetarli emas: o'qituvchiga haftada bir marta."""
    group = test.group
    teacher = group.teacher
    locale = locale_of(teacher.locale)
    year, week, _weekday = test.day.isocalendar()
    with translation.override(locale):
        return notify(
            teacher,
            Notification.Kind.DAILY_TEST_TEACHER,
            title=text(locale, "daily_test_short_title", group=group.name),
            body=text(
                locale,
                "daily_test_short_body",
                have=str(test.pool_size),
                need=str(test.questions_count),
            ),
            link=f"/dashboard/teaching/{group.pk}",
            dedupe_key=f"daily-test-short:{group.pk}:{year}-{week}",
        )


def remind(*, now: datetime | None = None) -> int:
    """20:00: bugungi testni hali tugatmaganlarga — 23:00 da yopiladi."""
    now = now or timezone.now()
    sent = 0
    tests = DailyTest.objects.filter(
        status=DailyTest.Status.OPEN, opens_at__lte=now, closes_at__gt=now
    ).select_related("group")
    for test in tests:
        done = set(
            test.attempts.filter(finished_at__isnull=False).values_list("student_id", flat=True)
        )
        for student in members(test.group_id, now=now):
            if student.pk in done:
                continue
            locale = locale_of(student.locale)
            with translation.override(locale):
                created = notify(
                    student,
                    Notification.Kind.DAILY_TEST,
                    title=text(locale, "daily_test_remind_title"),
                    body=text(locale, "daily_test_remind_body"),
                    link=LINK,
                    dedupe_key=f"daily-test-remind:{test.pk}:{student.pk}",
                )
            sent += created is not None
    return sent


def close_day(*, now: datetime | None = None) -> int:
    """23:00: vaqti tugagan testlar yopiladi; boshlab, tugatmaganlar javob bergan savollari bilan
    hisoblanadi (XP va coin ham shunga)."""
    now = now or timezone.now()
    closed = 0
    for test in DailyTest.objects.filter(status=DailyTest.Status.OPEN, closes_at__lte=now):
        for attempt in test.attempts.filter(finished_at__isnull=True):
            finish(attempt, now=test.closes_at)
        test.status = DailyTest.Status.CLOSED
        test.save(update_fields=["status", "updated_at"])
        closed += 1
    return closed


# --- O'quvchi ---


def today_for(user: Any, *, now: datetime | None = None) -> DailyTest | None:
    """O'quvchining bugungi (ochiq yoki yopilgan) testi — u a'zo bo'lgan guruhlardan biri."""
    now = now or timezone.now()
    return (
        DailyTest.objects.filter(group_id__in=student_group_ids(user), day=local_day(now))
        .exclude(status=DailyTest.Status.SKIPPED)
        .select_related("group__course")
        .order_by("group_id")
        .first()
    )


def is_member(test: DailyTest, user: Any, *, now: datetime | None = None) -> bool:
    return members(test.group_id, now=now).filter(pk=user.pk).exists()


def start(test: DailyTest, student: User, *, now: datetime | None = None) -> DailyAttempt:
    """Yangi urinish yoki davom ettirish (bir kunda bitta)."""
    now = now or timezone.now()
    existing = DailyAttempt.objects.filter(test=test, student=student).first()
    if existing is not None:
        return existing
    if not is_open(test, now):
        raise DailyTestError(_("Kunlik test yopilgan."))
    if not is_member(test, student, now=now):
        raise DailyTestError(_("Siz bu guruhda emassiz."))
    ids = choose(test, student)
    rng = random.SystemRandom()
    try:
        with transaction.atomic():
            return DailyAttempt.objects.create(
                test=test,
                student=student,
                question_ids=ids,
                seed=rng.randrange(1, 2**31),
                total=len(ids),
            )
    except IntegrityError:
        return DailyAttempt.objects.get(test=test, student=student)


def current(attempt: DailyAttempt) -> tuple[int, int, Question] | None:
    """Birinchi javobsiz savol: (tartib raqami, jami, savol). Hammasi javoblangan — None."""
    questions = load_questions(attempt.question_ids)
    ids = [question_id for question_id in attempt.question_ids if question_id in questions]
    answered = set(attempt.answers.values_list("question_id", flat=True))
    for index, question_id in enumerate(ids, 1):
        if question_id not in answered:
            return index, len(ids), questions[question_id]
    return None


def answer(
    attempt: DailyAttempt,
    question_id: int,
    response: dict[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    now = now or timezone.now()
    if attempt.finished_at is not None:
        raise DailyTestError(_("Test yakunlangan."))
    test = attempt.test
    if now >= test.closes_at or test.status != DailyTest.Status.OPEN:
        raise DailyTestError(_("Kunlik test yopildi — berilgan javoblaringiz saqlandi."))
    if question_id not in attempt.question_ids:
        raise DailyTestError(_("Bu savol ushbu testda yo'q."))
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if question is None:
        raise DailyTestError(_("Savol topilmadi."))
    layout = Layout.build(question, attempt.seed)
    private = layout.to_private(response)
    if private is None:
        raise DailyTestError(_("Javob formati noto'g'ri."))
    try:
        with transaction.atomic():
            DailyAnswer.objects.create(
                attempt=attempt,
                question=question,
                response=private,
                correct=grading.grade(question, layout.choices, private),
            )
    except IntegrityError as exc:
        raise DailyTestError(_("Bu savolga javob berilgan.")) from exc


def finish(attempt: DailyAttempt, *, now: datetime | None = None) -> Result:
    """Natija: to'g'ri javoblar soni; har to'g'ri javobga XP va coin (bir marta)."""
    now = now or timezone.now()
    config = rewards.settings()
    with transaction.atomic():
        locked = (
            DailyAttempt.objects.select_for_update()
            .select_related("test__group")
            .get(pk=attempt.pk)
        )
        if locked.finished_at is None:
            locked.correct = locked.answers.filter(correct=True).count()
            locked.total = len(locked.question_ids)
            locked.finished_at = min(now, locked.test.closes_at)
            locked.save(update_fields=["correct", "total", "finished_at"])
    xp = locked.correct * config.daily_test_xp
    coins = locked.correct * config.daily_test_coins
    if xp or coins:
        rewards.credit(
            locked.student_id,
            Entry.Reason.DAILY_TEST,
            key=f"daily-test:{locked.pk}",
            xp=xp,
            coins=coins,
            course_id=locked.test.group.course_id,
            note=f"{locked.correct}/{locked.total}",
        )
    attempt.correct, attempt.total, attempt.finished_at = (
        locked.correct,
        locked.total,
        locked.finished_at,
    )
    rows = day_rating(locked.test)
    place = next(
        (index for index, row in enumerate(rows, 1) if row.student_id == locked.student_id), 0
    )
    return Result(locked, xp, coins, place, len(rows))


# --- Reyting ---


def day_rating(test: DailyTest) -> list[Row]:
    """Kunlik: ko'p to'g'ri javob, teng bo'lsa — kim oldin tugatgan."""
    attempts = (
        test.attempts.filter(finished_at__isnull=False)
        .select_related("student")
        .order_by("-correct", "finished_at", "pk")
    )
    return [
        Row(attempt.student_id, short_name(attempt.student), attempt.correct, attempt.total)
        for attempt in attempts
    ]


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_rating(group: StudyGroup, day: date) -> list[Row]:
    """Haftalik (dushanbadan): to'g'ri javoblar yig'indisi."""
    attempts: QuerySet[DailyAttempt] = DailyAttempt.objects.filter(
        test__group=group,
        test__day__gte=week_start(day),
        test__day__lte=day,
        finished_at__isnull=False,
    )
    totals = (
        attempts.values("student_id")
        .annotate(points=Sum("correct"), questions=Sum("total"))
        .order_by("-points", "student_id")
    )
    people = {
        user.pk: user for user in User.objects.filter(pk__in=[row["student_id"] for row in totals])
    }
    return [
        Row(
            row["student_id"],
            short_name(people[row["student_id"]]),
            row["points"],
            row["questions"],
        )
        for row in totals
        if row["student_id"] in people
    ]


# --- Javoblar (test yopilgach) ---


def review(attempt: DailyAttempt) -> list[dict[str, Any]]:
    """Har savol: javob, to'g'ri javob va izoh (o'quvchi ko'rgan o'rinlar bilan)."""
    questions = load_questions(attempt.question_ids)
    answers = {item.question_id: item for item in attempt.answers.all()}
    items = []
    for question_id in attempt.question_ids:
        question = questions.get(question_id)
        if question is None:
            continue
        layout = Layout.build(question, attempt.seed)
        given = answers.get(question_id)
        items.append(
            {
                "question": question.pk,
                "correct": given.correct if given else False,
                "response": layout.to_public(given.response) if given else {},
                "correct_answer": layout.to_public(
                    grading.correct_answer(question, layout.choices)
                ),
                "explanation": question.explanation,
            }
        )
    return items


def attempt_payload(attempt: DailyAttempt, *, now: datetime | None = None) -> dict[str, Any]:
    """Saytda ishlash uchun: savollar (javobsiz) va berilgan javoblar (to'g'ri/noto'g'risiz) —
    botda boshlangan urinish ham shu yerda davom etadi."""
    now = now or timezone.now()
    questions = load_questions(attempt.question_ids)
    answers = {item.question_id: item for item in attempt.answers.all()}
    items, done = [], []
    for question_id in attempt.question_ids:
        question = questions.get(question_id)
        if question is None:
            continue
        layout = Layout.build(question, attempt.seed)
        items.append(layout.payload())
        given = answers.get(question_id)
        if given is not None:
            done.append({"question": question_id, "response": layout.to_public(given.response)})
    test = attempt.test
    return {
        "id": attempt.pk,
        "test_id": test.pk,
        "total": len(items),
        "closes_at": test.closes_at,
        "seconds_left": max(0, int((test.closes_at - now).total_seconds())),
        "finished": attempt.finished_at is not None,
        "questions": items,
        "answers": done,
    }


def saved(attempt: DailyAttempt, question_id: int) -> dict[str, Any]:
    """Saqlangan javob (o'quvchi ko'rgan o'rinlar bilan), bahosiz."""
    given = attempt.answers.select_related("question").get(question_id=question_id)
    question = Question.objects.prefetch_related("choices").get(pk=question_id)
    layout = Layout.build(question, attempt.seed)
    return {"question": question_id, "response": layout.to_public(given.response)}


def can_review(attempt: DailyAttempt, *, now: datetime | None = None) -> bool:
    """To'g'ri javoblar faqat test yopilgach (23:00) — aks holda kun ichida tarqalib ketardi."""
    now = now or timezone.now()
    test = attempt.test
    return test.status == DailyTest.Status.CLOSED or now >= test.closes_at
