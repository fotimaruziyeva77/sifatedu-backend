"""Jadvaldan darslar yaratish, qo'shilish, davomat, bekor qilish va xabarlar."""

from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone, translation

from apps.catalog.models import Lesson
from apps.core import events
from apps.learning.models import Enrollment, StudyGroup
from apps.notifications import services as notifications
from apps.notifications.models import Notification
from apps.notifications.texts import day_month, locale_of, text
from apps.users.models import User
from apps.users.roles import Role, has_role

from .models import Attendance, GroupLesson, LiveLesson, ScheduleSlot

AHEAD_DAYS = 14
# Shundan keyin qo'shilgan o'quvchi "kechikdi" deb belgilanadi.
LATE_AFTER = timedelta(minutes=10)
# O'tgan darslar ro'yxati va davomat foizi shuncha kunlik.
PAST_DAYS = 30
# Eng uzun dars (8 soat): "hozir ketayotgan" darslarni topish uchun.
LONGEST = timedelta(minutes=480)
LINK = "/dashboard/schedule"
# Kelmaganlarga xabar dars tugagach (o'qituvchi xatosini tuzatishga ulgursin).
ABSENT_NOTICE_AFTER = timedelta(minutes=15)


class LiveError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan sabab bilan (API 400)."""


# --- Jadval ---


def planned_times(
    group: StudyGroup, *, days: int = AHEAD_DAYS, now: datetime | None = None
) -> dict[datetime, ScheduleSlot]:
    """Haftalik jadval bo'yicha kelgusi darslar vaqti (Toshkent vaqtida)."""
    now = now or timezone.now()
    if group.status == StudyGroup.Status.FINISHED:
        return {}
    slots = list(group.slots.all())
    zone = timezone.get_default_timezone()
    today = timezone.localdate(now, zone)
    planned: dict[datetime, ScheduleSlot] = {}
    for offset in range(days):
        day = today + timedelta(days=offset)
        if group.starts_on and day < group.starts_on:
            continue
        for slot in slots:
            if slot.weekday != day.weekday():
                continue
            starts = timezone.make_aware(datetime.combine(day, slot.starts_at), zone)
            if starts > now:
                planned[starts] = slot
    return planned


def lesson_defaults(group: StudyGroup, slot: ScheduleSlot) -> dict[str, Any]:
    online = group.study_format == LiveLesson.Kind.ONLINE
    return {
        "duration_min": slot.duration_min,
        "kind": LiveLesson.Kind.ONLINE if online else LiveLesson.Kind.OFFLINE,
        "meet_url": group.meet_url if online else "",
        "room": "" if online else group.room,
    }


def generate(group: StudyGroup, *, now: datetime | None = None) -> int:
    """Yetishmagan darslarni yaratadi. Bor dars (bekor qilingani ham) qayta yaratilmaydi."""
    created = 0
    for starts, slot in planned_times(group, now=now).items():
        _lesson, new = LiveLesson.objects.get_or_create(
            group=group,
            starts_at=starts,
            defaults={**lesson_defaults(group, slot), "generated": True},
        )
        created += new
    return created


@transaction.atomic
def sync(group: StudyGroup, *, now: datetime | None = None) -> tuple[int, int]:
    """Jadval yoki guruh havolasi o'zgarganda: kelgusi avtomatik darslar moslanadi. Qo'lda
    o'zgartirilgan, bekor qilingan va davomati bor darslarga tegilmaydi (ID lar saqlanadi —
    yuborilgan eslatmalar takrorlanmaydi)."""
    now = now or timezone.now()
    planned = planned_times(group, now=now)
    untouched = (
        group.live_lessons.filter(generated=True, starts_at__gt=now, canceled_at__isnull=True)
        .annotate(marks=Count("attendance"))
        .filter(marks=0)
    )
    removed = 0
    for lesson in untouched:
        slot = planned.get(lesson.starts_at)
        if slot is None:
            lesson.delete()
            removed += 1
            continue
        wanted = lesson_defaults(group, slot)
        changed = [field for field, value in wanted.items() if getattr(lesson, field) != value]
        if changed:
            for field in changed:
                setattr(lesson, field, wanted[field])
            lesson.save(update_fields=[*changed, "updated_at"])
    return generate(group, now=now), removed


# --- Kimlar ---


def members(group_id: int, *, now: datetime | None = None) -> QuerySet[User]:
    """Guruhning faol o'quvchilari (to'lov muddati o'tganlar — yo'q)."""
    now = now or timezone.now()
    return (
        User.objects.filter(
            Q(enrollments__group_id=group_id)
            & Q(enrollments__status=Enrollment.Status.ACTIVE)
            & (Q(enrollments__expires_at__isnull=True) | Q(enrollments__expires_at__gt=now)),
            is_active=True,
        )
        .distinct()
        .order_by("first_name", "last_name", "pk")
    )


def student_group_ids(user: Any) -> set[int]:
    if not getattr(user, "is_authenticated", False):
        return set()
    now = timezone.now()
    return set(
        Enrollment.objects.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
            user=user,
            status=Enrollment.Status.ACTIVE,
            group__isnull=False,
        ).values_list("group_id", flat=True)
    )


def teacher_group_ids(user: Any) -> set[int]:
    if not getattr(user, "is_authenticated", False):
        return set()
    return set(
        StudyGroup.objects.filter(teacher=user)
        .exclude(status=StudyGroup.Status.FINISHED)
        .values_list("pk", flat=True)
    )


def has_schedule(user: Any) -> bool:
    return bool(student_group_ids(user) or teacher_group_ids(user))


def can_manage(user: Any, lesson: LiveLesson) -> bool:
    """Davomat, bekor qilish, yozuv: guruh o'qituvchisi, menejer va admin."""
    return lesson.group.teacher_id == user.pk or has_role(user, Role.ADMIN, Role.MANAGER)


# --- Jadval sahifasi ---


def lessons_for(user: Any, *, upcoming: bool, now: datetime | None = None) -> list[LiveLesson]:
    now = now or timezone.now()
    group_ids = student_group_ids(user) | teacher_group_ids(user)
    queryset = LiveLesson.objects.filter(group_id__in=group_ids).select_related(
        "group__course", "topic"
    )
    if upcoming:
        found = queryset.filter(
            starts_at__gte=now - LONGEST, starts_at__lte=now + timedelta(days=AHEAD_DAYS)
        ).order_by("starts_at")
        return [lesson for lesson in found if lesson.ends_at > now]
    found = queryset.filter(
        starts_at__gte=now - timedelta(days=PAST_DAYS), starts_at__lt=now
    ).order_by("-starts_at")
    return [lesson for lesson in found if lesson.ends_at <= now]


def lesson_payload(
    lesson: LiveLesson, user: Any, marks: dict[int, str], now: datetime
) -> dict[str, Any]:
    group = lesson.group
    teacher = group.teacher_id == user.pk
    online = lesson.kind == LiveLesson.Kind.ONLINE and bool(lesson.meet_url)
    ended = lesson.ends_at <= now
    return {
        "id": lesson.pk,
        "group_id": group.pk,
        "group": group.name,
        "course_title": str(group.course.title),
        "course_slug": group.course.slug,
        "title": lesson.title or (str(lesson.topic.title) if lesson.topic else ""),
        "kind": lesson.kind,
        "starts_at": lesson.starts_at,
        "ends_at": lesson.ends_at,
        "opens_at": lesson.opens_at,
        "duration_min": lesson.duration_min,
        "room": lesson.room,
        "notes": lesson.notes,
        "canceled": lesson.is_canceled,
        "cancel_reason": lesson.cancel_reason,
        "join_url": f"/api/v1/live/{lesson.pk}/join/" if online and not lesson.is_canceled else "",
        "can_join": online and not lesson.is_canceled and lesson.opens_at <= now < lesson.ends_at,
        "recording_url": lesson.recording_url if ended else "",
        "attendance": None if teacher else (marks.get(lesson.pk) or None),
        "is_teacher": teacher,
    }


def schedule(user: Any, *, upcoming: bool, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or timezone.now()
    lessons = lessons_for(user, upcoming=upcoming, now=now)
    marks = dict(
        Attendance.objects.filter(live_lesson__in=lessons, student=user)
        .exclude(status="")
        .values_list("live_lesson_id", "status")
    )
    return [lesson_payload(lesson, user, marks, now) for lesson in lessons]


# --- Qo'shilish ---


def join(lesson: LiveLesson, user: Any, *, now: datetime | None = None) -> str:
    """Meet havolasi. O'quvchi qo'shilgani yoziladi va oldindan "keldi" deb belgilanadi."""
    now = now or timezone.now()
    if lesson.is_canceled:
        raise LiveError("Bu dars bekor qilingan.")
    if lesson.kind != LiveLesson.Kind.ONLINE or not lesson.meet_url:
        raise LiveError("Bu dars onlayn emas.")
    if not lesson.opens_at <= now < lesson.ends_at:
        raise LiveError("Qo'shilish dars boshlanishidan 15 daqiqa oldin ochiladi.")
    if members(lesson.group_id, now=now).filter(pk=user.pk).exists():
        record, _created = Attendance.objects.get_or_create(live_lesson=lesson, student=user)
        if record.joined_at is None:
            record.joined_at = now
            if not record.status:
                late = now > lesson.starts_at + LATE_AFTER
                record.status = Attendance.Status.LATE if late else Attendance.Status.PRESENT
            record.save(update_fields=["joined_at", "status"])
    return lesson.meet_url


# --- O'qituvchi ---


def roster(lesson: LiveLesson) -> list[dict[str, Any]]:
    """Guruh o'quvchilari va ularning shu darsdagi holati (guruhdan chiqqan, lekin belgilangan
    o'quvchilar ham ko'rinadi)."""
    records = {record.student_id: record for record in lesson.attendance.select_related("student")}
    students = list(members(lesson.group_id))
    known = {student.pk for student in students}
    students += [record.student for sid, record in records.items() if sid not in known]
    return [
        {
            "id": student.pk,
            "name": student.get_full_name() or student.phone,
            "avatar": student.avatar.url if student.avatar else "",
            "status": records[student.pk].status if student.pk in records else "",
            "joined_at": records[student.pk].joined_at if student.pk in records else None,
        }
        for student in students
    ]


def save_attendance(
    lesson: LiveLesson, by: User, statuses: dict[int, str], *, now: datetime | None = None
) -> None:
    now = now or timezone.now()
    if lesson.is_canceled:
        raise LiveError("Bekor qilingan darsda davomat belgilanmaydi.")
    if now < lesson.opens_at:
        raise LiveError("Davomat dars boshlanishidan 15 daqiqa oldin ochiladi.")
    allowed = {row["id"] for row in roster(lesson)}
    if set(statuses) - allowed:
        raise LiveError("Ro'yxatda yo'q o'quvchi.")
    with transaction.atomic():
        for student_id, status in statuses.items():
            record, _created = Attendance.objects.get_or_create(
                live_lesson=lesson, student_id=student_id
            )
            # "Qo'shilish" bilan qo'yilgan holat o'qituvchi saqlaganda tasdiqlanadi.
            if record.status != status or record.marked_by_id is None:
                record.status = status
                record.marked_by = by
                record.marked_at = now
                record.save(update_fields=["status", "marked_by", "marked_at"])
                events.attendance_marked.send(
                    sender=Attendance,
                    user_id=student_id,
                    course_id=lesson.group.course_id,
                    live_lesson_id=lesson.pk,
                    status=status,
                )


def cancel(lesson: LiveLesson, reason: str, *, by: Any = None, now: datetime | None = None) -> None:
    """O'quvchilarga xabar; o'qituvchiga — agar darsni boshqa odam (menejer) bekor qilgan bo'lsa."""
    now = now or timezone.now()
    if lesson.is_canceled:
        raise LiveError("Dars allaqachon bekor qilingan.")
    if lesson.starts_at <= now:
        raise LiveError("Boshlangan darsni bekor qilib bo'lmaydi.")
    lesson.canceled_at = now
    lesson.cancel_reason = reason.strip()[:200]
    lesson.save(update_fields=["canceled_at", "cancel_reason", "updated_at"])
    by_teacher = by is not None and by.pk == lesson.group.teacher_id
    notify_group(
        lesson, "canceled", Notification.Kind.LIVE_CANCELED, teacher=not by_teacher, now=now
    )


def set_recording(lesson: LiveLesson, url: str) -> None:
    """Yozuv havolasi birinchi marta qo'yilganda o'quvchilarga xabar."""
    lesson.recording_url = url
    lesson.save(update_fields=["recording_url", "updated_at"])
    if url:
        notify_group(lesson, "recording", Notification.Kind.LIVE_RECORDING, teacher=False)


# --- Dars o'tildi (offlayn) ---


def cover(lesson: LiveLesson, topic: Lesson, by: Any, *, now: datetime | None = None) -> bool:
    """Darsga mavzu qo'yiladi va u guruh uchun ochiladi (test va vazifalari). Yangi ochilgan
    bo'lsa — guruh o'quvchilariga xabar."""
    now = now or timezone.now()
    if topic.module.course_id != lesson.group.course_id:
        raise LiveError("Bu dars guruh kursiga tegishli emas.")
    if lesson.is_canceled:
        raise LiveError("Bekor qilingan darsni o'tilgan deb belgilab bo'lmaydi.")
    if now < lesson.opens_at:
        raise LiveError("Dars hali boshlanmagan.")
    if lesson.topic_id != topic.pk:
        lesson.topic = topic
        lesson.save(update_fields=["topic", "updated_at"])
    record, created = GroupLesson.objects.get_or_create(
        group=lesson.group, lesson=topic, defaults={"live_lesson": lesson, "opened_by": by}
    )
    if created:
        announce(record)
    return created


def uncover(lesson: LiveLesson) -> int:
    """Xato belgilangan bo'lsa: shu darsdan ochilgan belgi olib tashlanadi (yuborilgan xabar
    qaytmaydi)."""
    deleted, _rows = GroupLesson.objects.filter(live_lesson=lesson).delete()
    return deleted


def announce(record: GroupLesson) -> int:
    """Guruhga (darsda bo'lmaganlarga ham): dars ochildi. Testi bo'lsa — Telegram'da
    "Testni boshlash" tugmasi, test botning o'zida ishlanadi."""
    from apps.quizzes.models import Quiz

    lesson = record.lesson
    group = record.group
    course = group.course
    quiz_id = (
        Quiz.objects.filter(lesson=lesson, questions__isnull=False)
        .values_list("pk", flat=True)
        .first()
    )
    sent = 0
    for student in members(group.pk):
        locale = locale_of(student.locale)
        with translation.override(locale):
            title = text(locale, "lesson_opened_title", lesson=str(lesson.title))
            body = text(locale, "lesson_opened_body", group=group.name, course=str(course.title))
        created = notifications.notify(
            student,
            Notification.Kind.LESSON_OPENED,
            title=title,
            body=body,
            link=f"/dashboard/courses/{course.slug}/lessons/{lesson.pk}",
            dedupe_key=f"lesson-open:{record.pk}:{student.pk}",
            quiz_id=quiz_id,
        )
        sent += created is not None
    return sent


def course_lessons(lesson: LiveLesson) -> list[dict[str, Any]]:
    """O'qituvchi mavzu tanlashi uchun: guruh kursining darslari va qaysilari ochilgan."""
    group = lesson.group
    covered = set(group.covered_lessons.values_list("lesson_id", flat=True))
    rows = (
        Lesson.objects.filter(module__course_id=group.course_id)
        .select_related("module")
        .order_by("module__order", "module__id", "order", "id")
    )
    return [
        {
            "id": row.pk,
            "title": str(row.title),
            "module": str(row.module.title),
            "covered": row.pk in covered,
        }
        for row in rows
    ]


# --- Xabarlar ---


def moment(lesson: LiveLesson, locale: str) -> str:
    local = timezone.localtime(lesson.starts_at)
    return f"{day_month(local.date(), locale)}, {local:%H:%M}"


def place(lesson: LiveLesson, locale: str) -> str:
    if lesson.kind == LiveLesson.Kind.ONLINE:
        return text(locale, "live_place_online")
    if lesson.room:
        return text(locale, "live_place_room", room=lesson.room)
    return text(locale, "live_place_offline")


def message(lesson: LiveLesson, step: str, locale: str) -> tuple[str, str]:
    with translation.override(locale):
        course = str(lesson.group.course.title)
    params = {
        "when": moment(lesson, locale),
        "time": f"{timezone.localtime(lesson.starts_at):%H:%M}",
        "group": lesson.group.name,
        "course": course,
        "place": place(lesson, locale),
        "reason": lesson.cancel_reason or text(locale, "live_no_reason"),
    }
    return text(locale, f"live_{step}_title", **params), text(locale, f"live_{step}_body", **params)


def notify_one(lesson: LiveLesson, user: User, step: str, kind: str) -> bool:
    locale = locale_of(user.locale)
    title, body = message(lesson, step, locale)
    created = notifications.notify(
        user,
        kind,
        title=title,
        body=body,
        link=LINK,
        dedupe_key=f"live:{lesson.pk}:{step}:{user.pk}",
    )
    return created is not None


def notify_group(
    lesson: LiveLesson,
    step: str,
    kind: str,
    *,
    teacher: bool = True,
    now: datetime | None = None,
) -> int:
    people = list(members(lesson.group_id, now=now))
    if teacher and lesson.group.teacher_id not in {person.pk for person in people}:
        people.append(lesson.group.teacher)
    return sum(notify_one(lesson, person, step, kind) for person in people)


def remind(*, now: datetime | None = None) -> int:
    """Kun ichidagi (24 soat ichida) va 30 daqiqalik eslatmalar; tugagan darsda kelmaganlarga
    xabar. Har 5 daqiqada ishlaydi, har xabar bir marta."""
    now = now or timezone.now()
    sent = 0
    upcoming = LiveLesson.objects.filter(
        canceled_at__isnull=True, starts_at__gt=now, starts_at__lte=now + timedelta(hours=24)
    ).select_related("group__course", "group__teacher")
    for lesson in upcoming:
        left = lesson.starts_at - now
        if left <= timedelta(minutes=35):
            sent += notify_group(lesson, "soon", Notification.Kind.LIVE_REMINDER, now=now)
        elif left > timedelta(hours=2):
            sent += notify_group(lesson, "day", Notification.Kind.LIVE_REMINDER, now=now)
    finished = (
        LiveLesson.objects.filter(
            canceled_at__isnull=True,
            starts_at__gte=now - timedelta(days=2),
            starts_at__lte=now,
            attendance__status=Attendance.Status.ABSENT,
        )
        .distinct()
        .select_related("group__course")
    )
    for lesson in finished:
        if lesson.ends_at + ABSENT_NOTICE_AFTER > now:
            continue
        for record in lesson.attendance.filter(status=Attendance.Status.ABSENT).select_related(
            "student"
        ):
            sent += notify_one(lesson, record.student, "absent", Notification.Kind.LIVE_ABSENT)
    return sent


# --- Statistika ---


def attendance_rates(
    user_ids: list[int], group_id: int, *, now: datetime | None = None
) -> dict[int, int]:
    """Oxirgi 30 kun: (keldi + kechikdi) / (keldi + kechikdi + kelmadi); "sababli" hisoblanmaydi."""
    now = now or timezone.now()
    rows = (
        Attendance.objects.filter(
            student_id__in=user_ids,
            live_lesson__group_id=group_id,
            live_lesson__canceled_at__isnull=True,
            live_lesson__starts_at__gte=now - timedelta(days=PAST_DAYS),
            status__in=[
                Attendance.Status.PRESENT,
                Attendance.Status.LATE,
                Attendance.Status.ABSENT,
            ],
        )
        .values("student_id")
        .annotate(came=Count("pk", filter=~Q(status=Attendance.Status.ABSENT)), total=Count("pk"))
    )
    return {row["student_id"]: round(row["came"] * 100 / row["total"]) for row in rows}


def repeated_absences(*, now: datetime | None = None) -> list[tuple[int, int]]:
    """(o'quvchi, guruh): oxirgi ikkita belgilangan darsda ham kelmagan (30 kun ichida)."""
    now = now or timezone.now()
    rows = (
        Attendance.objects.filter(
            live_lesson__canceled_at__isnull=True,
            live_lesson__starts_at__gte=now - timedelta(days=PAST_DAYS),
            live_lesson__starts_at__lte=now,
        )
        .exclude(status="")
        .order_by("student_id", "live_lesson__group_id", "-live_lesson__starts_at")
        .values_list("student_id", "live_lesson__group_id", "status")
    )
    latest: dict[tuple[int, int], list[str]] = {}
    for student_id, group_id, status in rows:
        statuses = latest.setdefault((student_id, group_id), [])
        if len(statuses) < 2:
            statuses.append(status)
    return [
        key
        for key, statuses in latest.items()
        if statuses == [Attendance.Status.ABSENT, Attendance.Status.ABSENT]
    ]
