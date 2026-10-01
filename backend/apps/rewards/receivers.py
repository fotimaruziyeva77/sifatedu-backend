"""O'qish hodisalari → XP, coin, shtraf va kunlik topshiriqlar.

Har tinglovchi o'z savepoint'ida (`services.safely`): mukofotdagi xato darsni, testni yoki
vazifani buzmaydi — faqat log'ga yoziladi.
"""

from typing import Any

from django.dispatch import receiver

from apps.core import events

from . import daily, referral, services
from .models import DailyTask, Entry

Kind = DailyTask.Kind
Reason = Entry.Reason


@receiver(events.lesson_completed)
@services.safely
def lesson_completed(
    sender: Any, *, user_id: int, course_id: int, lesson_id: int, **kwargs: Any
) -> None:
    config = services.settings()
    services.reward(
        user_id,
        Reason.LESSON,
        config.lesson_xp,
        key=f"lesson:{user_id}:{lesson_id}",
        course_id=course_id,
    )
    daily.progress(user_id, Kind.LESSON, course_id=course_id, lesson_id=lesson_id)
    referral.friend_lesson(user_id)


@receiver(events.quiz_passed)
@services.safely
def quiz_passed(
    sender: Any, *, user_id: int, course_id: int, quiz_id: int, first: bool = True, **kwargs: Any
) -> None:
    if first:
        services.reward(
            user_id,
            Reason.QUIZ,
            services.settings().quiz_xp,
            key=f"quiz:{user_id}:{quiz_id}",
            course_id=course_id,
        )
    daily.progress(user_id, Kind.QUIZ, course_id=course_id, quiz_id=quiz_id)


@receiver(events.homework_submitted)
@services.safely
def homework_submitted(
    sender: Any,
    *,
    user_id: int,
    course_id: int,
    assignment_id: int,
    late: bool = False,
    **kwargs: Any,
) -> None:
    config = services.settings()
    # Mukofot — birinchi topshirilganda; qayta topshirish (izohdan keyin) — yangi XP emas.
    services.reward(
        user_id,
        Reason.HOMEWORK,
        config.homework_xp,
        key=f"homework:{user_id}:{assignment_id}",
        course_id=course_id,
    )
    if late:
        services.penalize(
            user_id,
            Reason.HOMEWORK_LATE,
            config.homework_late_penalty,
            key=f"homework-late:{user_id}:{assignment_id}",
            course_id=course_id,
        )
    daily.progress(user_id, Kind.HOMEWORK, course_id=course_id, assignment_id=assignment_id)


# Davomat holati → yozuv. Sababli (EXCUSED) — hech narsa.
ATTENDANCE = {
    "PRESENT": Reason.ATTENDANCE,
    "LATE": Reason.LATE,
    "ABSENT": Reason.ABSENT,
}


@receiver(events.attendance_marked)
@services.safely
def attendance_marked(
    sender: Any,
    *,
    user_id: int,
    course_id: int,
    live_lesson_id: int,
    status: str,
    **kwargs: Any,
) -> None:
    """O'qituvchi davomatni o'zgartirsa, oldingi yozuv bekor qilinib, yangisi yoziladi."""
    key = f"live:{user_id}:{live_lesson_id}"
    wanted = ATTENDANCE.get(status)
    previous = services.active(key)
    if previous is not None:
        if previous.reason == wanted:
            return
        services.cancel(previous, reason="Davomat o'zgartirildi")
    config = services.settings()
    if wanted == Reason.ATTENDANCE:
        services.reward(user_id, wanted, config.attendance_xp, key=key, course_id=course_id)
        daily.progress(user_id, Kind.LIVE, live_lesson_id=live_lesson_id)
    elif wanted == Reason.LATE:
        services.penalize(user_id, wanted, config.late_penalty, key=key, course_id=course_id)
    elif wanted == Reason.ABSENT:
        services.penalize(user_id, wanted, config.absent_penalty, key=key, course_id=course_id)


@receiver(events.exam_finalized)
@services.safely
def exam_finalized(
    sender: Any,
    *,
    user_id: int,
    course_id: int,
    exam_id: int,
    passed: bool = False,
    **kwargs: Any,
) -> None:
    if passed:
        services.reward(
            user_id,
            Reason.EXAM,
            services.settings().exam_xp,
            key=f"exam:{user_id}:{exam_id}",
            course_id=course_id,
        )


@receiver(events.order_paid)
@services.safely
def order_paid(sender: Any, *, order: Any, **kwargs: Any) -> None:
    referral.order_paid(order)
