"""Kunlik topshiriqlar: har kuni 09:00 da har bir faol o'quvchiga 3 ta — qayerga yetganiga qarab.

Turlari: keyingi darsni ko'rish, dars testidan o'tish, botda takrorlash (5 savol), uy vazifasini
topshirish, bugungi darsga vaqtida kelish. Bugungi dars bo'lsa — albatta; qolganlari har kuni
boshqacha tartibda (kechagisidan farqli turlar oldinda). Bajarilgani hodisalardan o'zi
belgilanadi; uchalasi bajarilsa — bonus va seriya. Kun oxirida bajarilmagan bo'lsa — shtraf va
seriya uziladi.
"""

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.learning import access
from apps.learning.models import Enrollment
from apps.learning.views import completed_ids, course_card, with_program
from apps.live.models import LiveLesson
from apps.live.services import student_group_ids
from apps.quizzes.models import Attempt, Question
from apps.users.models import SocialAccount, User

from . import services
from .models import DailyTask, Entry, Wallet

COUNT = 3
REVIEW_SIZE = 5
Kind = DailyTask.Kind


@dataclass
class Candidate:
    kind: str
    title: str
    course_id: int | None = None
    lesson_id: int | None = None
    quiz_id: int | None = None
    assignment_id: int | None = None
    live_lesson_id: int | None = None


def students() -> QuerySet[User]:
    """Faol o'quvchilar: kamida bitta faol (muddati o'tmagan) yozilishi bor, xodim emas."""
    now = timezone.now()
    return User.objects.filter(
        Q(enrollments__status=Enrollment.Status.ACTIVE)
        & (Q(enrollments__expires_at__isnull=True) | Q(enrollments__expires_at__gt=now)),
        is_active=True,
        is_staff=False,
    ).distinct()


def has_telegram(user: User) -> bool:
    return SocialAccount.objects.filter(
        user=user, provider=SocialAccount.Provider.TELEGRAM, blocked_at__isnull=True
    ).exists()


def review_pool(user: Any) -> list[int]:
    """Takrorlash uchun savollar: o'quvchi o'tgan dars testlaridan."""
    passed = Attempt.objects.filter(student_id=user.pk, passed=True).values("quiz_id")
    return list(Question.objects.filter(quiz_id__in=passed).values_list("pk", flat=True))


def next_lesson(user: User) -> Candidate | None:
    for course in with_program(access.enrolled_courses(user)).order_by("order", "id"):
        card = course_card(
            course, completed_ids(user, course), None, access.quiz_gate(user, course.pk)
        )
        if card["completed_count"] >= card["lesson_count"]:
            continue
        lessons = {
            lesson.pk: lesson for module in course.modules.all() for lesson in module.lessons.all()
        }
        upcoming = lessons.get(card["next_lesson_id"])
        if upcoming is not None:
            return Candidate(Kind.LESSON, str(upcoming.title), course.pk, lesson_id=upcoming.pk)
    return None


def open_quiz(user: User) -> Candidate | None:
    from apps.bot.quiz import available  # bot → rewards menyusi: import aylanmasin

    found, _passed = available(user)
    if not found:
        return None
    item = found[0]
    lesson = item.quiz.lesson
    return Candidate(
        Kind.QUIZ,
        str(lesson.title),
        lesson.module.course_id,
        lesson_id=lesson.pk,
        quiz_id=item.quiz.pk,
    )


def open_homework(user: User) -> Candidate | None:
    from apps.homework.services import my_homework

    for item in my_homework(user, access.enrolled_courses(user)):
        if item["status"] in ("NOT_SUBMITTED", "CHANGES_REQUESTED"):
            return Candidate(
                Kind.HOMEWORK,
                str(item["title"] or item["lesson_title"]),
                lesson_id=item["lesson_id"],
                assignment_id=item["assignment_id"],
            )
    return None


def todays_live(user: User, now: datetime) -> Candidate | None:
    end = timezone.localtime(now).replace(hour=23, minute=59, second=59)
    lesson = (
        LiveLesson.objects.filter(
            group_id__in=student_group_ids(user),
            starts_at__gt=now,
            starts_at__lte=end,
            canceled_at__isnull=True,
        )
        .select_related("group__course", "topic")
        .order_by("starts_at")
        .first()
    )
    if lesson is None:
        return None
    title = lesson.title or (
        str(lesson.topic.title) if lesson.topic else str(lesson.group.course.title)
    )
    return Candidate(Kind.LIVE, title, lesson.group.course_id, live_lesson_id=lesson.pk)


def candidates(user: User, now: datetime) -> list[Candidate]:
    found = [
        todays_live(user, now),
        next_lesson(user),
        open_quiz(user),
        open_homework(user),
    ]
    if has_telegram(user) and len(review_pool(user)) >= REVIEW_SIZE:
        found.append(Candidate(Kind.REVIEW, ""))
    return [item for item in found if item is not None]


def pick(user: User, found: list[Candidate], day: date) -> list[Candidate]:
    """Bugungi dars — albatta; qolganlari kunga qarab aralash, kechagi turlar oxirida."""
    yesterday = set(
        DailyTask.objects.filter(user=user, day=day - timedelta(days=1)).values_list(
            "kind", flat=True
        )
    )
    live = [item for item in found if item.kind == Kind.LIVE]
    rest = [item for item in found if item.kind != Kind.LIVE]
    # Kriptografik emas: shunchaki har kuni boshqacha, lekin qayta hisoblansa bir xil tartib.
    random.Random(f"{user.pk}:{day.isoformat()}").shuffle(rest)  # noqa: S311
    rest.sort(key=lambda item: item.kind in yesterday)
    return (live + rest)[:COUNT]


def assign(user: User, day: date, *, now: datetime | None = None) -> list[DailyTask]:
    now = now or timezone.now()
    if DailyTask.objects.filter(user=user, day=day).exists():
        return list(DailyTask.objects.filter(user=user, day=day))
    tasks = [
        DailyTask(
            user=user,
            day=day,
            kind=item.kind,
            course_id=item.course_id,
            lesson_id=item.lesson_id,
            quiz_id=item.quiz_id,
            assignment_id=item.assignment_id,
            live_lesson_id=item.live_lesson_id,
            title=item.title[:300],
        )
        for item in pick(user, candidates(user, now), day)
    ]
    return DailyTask.objects.bulk_create(tasks, ignore_conflicts=True)


def generate(*, now: datetime | None = None) -> int:
    """09:00: hamma faol o'quvchiga bugungi topshiriqlar (allaqachon borlarga — yo'q)."""
    if not services.settings().daily_tasks:
        return 0
    now = now or timezone.now()
    day = timezone.localdate(now)
    created = 0
    for user in students().exclude(daily_tasks__day=day):
        created += bool(assign(user, day, now=now))
    return created


def today(user: Any, *, now: datetime | None = None) -> list[DailyTask]:
    day = timezone.localdate(now or timezone.now())
    return list(
        DailyTask.objects.filter(user_id=user.pk, day=day).select_related(
            "course", "lesson", "quiz", "live_lesson"
        )
    )


def matches(task: DailyTask, kind: str, **target: Any) -> bool:
    if task.kind != kind or task.done_at is not None:
        return False
    if kind == Kind.LIVE:
        return task.live_lesson_id == target.get("live_lesson_id")
    course_id = target.get("course_id")
    # Dars, test va vazifa — shu kursdagi istalgani ham hisoblanadi (o'quvchi oldinroq o'tgan
    # bo'lishi mumkin); kurs belgilanmagan topshiriqqa — istalgan kurs.
    return task.course_id is None or course_id is None or task.course_id == course_id


def progress(user_id: int, kind: str, *, now: datetime | None = None, **target: Any) -> bool:
    """Hodisa bugungi topshiriqni bajargan bo'lsa — belgilaydi; hammasi bajarilsa — bonus."""
    now = now or timezone.now()
    day = timezone.localdate(now)
    with transaction.atomic():
        tasks = list(DailyTask.objects.select_for_update().filter(user_id=user_id, day=day))
        task = next((item for item in tasks if matches(item, kind, **target)), None)
        if task is None:
            return False
        task.done_at = now
        task.save(update_fields=["done_at"])
        if all(item.done_at is not None for item in tasks):
            finish_day(user_id, day, tasks)
    return True


def finish_day(user_id: int, day: date, tasks: list[DailyTask]) -> None:
    config = services.settings()
    services.reward(
        user_id, Entry.Reason.DAILY, config.daily_bonus_xp, key=f"daily:{user_id}:{day.isoformat()}"
    )
    services.wallet_of(user_id)
    wallet = Wallet.objects.select_for_update().get(user_id=user_id)
    if wallet.streak_day == day:
        return
    # Seriya: oldingi to'liq kundan beri topshiriq berilmagan kunlar seriyani uzmaydi.
    missed = (
        wallet.streak_day is None
        or DailyTask.objects.filter(
            user_id=user_id, day__gt=wallet.streak_day, day__lt=day
        ).exists()
    )
    wallet.streak = 1 if missed else wallet.streak + 1
    wallet.best_streak = max(wallet.best_streak, wallet.streak)
    wallet.streak_day = day
    wallet.save(update_fields=["streak", "best_streak", "streak_day", "updated_at"])


def close(*, now: datetime | None = None) -> int:
    """Kun oxiri (ertasi 00:10): kechagi topshiriqlari bajarilmaganlarga shtraf, seriya uziladi."""
    now = now or timezone.now()
    day = timezone.localdate(now) - timedelta(days=1)
    config = services.settings()
    users = (
        DailyTask.objects.filter(day=day)
        .values("user_id")
        .annotate(total=Count("pk"), done=Count("pk", filter=Q(done_at__isnull=False)))
        .filter(total__gt=0)
    )
    count = 0
    for row in users:
        if row["done"] >= row["total"]:
            continue
        entry = services.penalize(
            row["user_id"],
            Entry.Reason.DAILY_MISSED,
            config.daily_missed_penalty,
            key=f"daily-missed:{row['user_id']}:{day.isoformat()}",
        )
        Wallet.objects.filter(user_id=row["user_id"]).update(streak=0)
        count += entry is not None
    return count
