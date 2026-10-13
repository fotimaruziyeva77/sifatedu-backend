"""Admin bosh sahifasidagi «O'quv jarayoni»: bugungi darslar, guruhlar va imtihonlar.

Davrga bog'liq emas — hozirgi holat. Havolalar saytdagi kabinetga: guruh va dars sahifalari
kabinetga kira oladiganlarga (admin, menejer, guruh o'qituvchisi), imtihonni baholash —
imtihonni boshqaradiganlarga (`exams.services.can_manage`).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.dailytest.models import DailyAttempt, DailyTest
from apps.exams import payloads
from apps.exams import services as exams
from apps.exams.models import Exam, ExamResult, TaskAnswer
from apps.homework.models import Submission
from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import Attendance, LiveLesson
from apps.users.models import User
from apps.users.roles import manages_groups

from .metrics import day_start, site_link

# Yopilgan imtihon shuncha kun ro'yxatda turadi (baholash va natijalar uchun).
EXAM_RECENT = timedelta(days=14)
MAX_EXAMS = 6
# Davomat foizi — oxirgi 30 kun (guruh sahifasidagi kabi).
ATTENDANCE_DAYS = 30


def can_open_group(viewer: User, group: StudyGroup) -> bool:
    return group.teacher_id == viewer.pk or manages_groups(viewer)


@dataclass(frozen=True)
class LessonRow:
    lesson: LiveLesson
    # canceled | upcoming | live | marked | unmarked
    state: str
    came: int
    late: int
    absent: int
    url: str


def lesson_state(lesson: LiveLesson, marked: int, now: datetime) -> str:
    if lesson.is_canceled:
        return "canceled"
    if now < lesson.starts_at:
        return "upcoming"
    if now < lesson.ends_at:
        return "live"
    return "marked" if marked else "unmarked"


def lessons_today(viewer: User, now: datetime | None = None) -> list[LessonRow]:
    """Bugungi jonli darslar (Toshkent vaqti) va davomati: o'qituvchi belgilagan holatlar."""
    now = now or timezone.now()
    start = day_start(timezone.localdate(now))
    lessons = list(
        LiveLesson.objects.filter(starts_at__gte=start, starts_at__lt=start + timedelta(days=1))
        .select_related("group__course", "group__teacher")
        .order_by("starts_at", "pk")
    )
    counts: dict[int, dict[str, int]] = {}
    for row in (
        Attendance.objects.filter(live_lesson__in=lessons, marked_by__isnull=False)
        .values("live_lesson_id", "status")
        .annotate(count=Count("pk"))
    ):
        counts.setdefault(row["live_lesson_id"], {})[row["status"]] = row["count"]
    rows = []
    for lesson in lessons:
        statuses = counts.get(lesson.pk, {})
        rows.append(
            LessonRow(
                lesson=lesson,
                state=lesson_state(lesson, sum(statuses.values()), now),
                came=statuses.get(Attendance.Status.PRESENT, 0),
                late=statuses.get(Attendance.Status.LATE, 0),
                absent=statuses.get(Attendance.Status.ABSENT, 0),
                url=(
                    site_link(viewer, f"/dashboard/teaching/live/{lesson.pk}")
                    if can_open_group(viewer, lesson.group)
                    else ""
                ),
            )
        )
    return rows


@dataclass(frozen=True)
class GroupRow:
    group: StudyGroup
    students: int
    # Oxirgi 30 kun: (keldi + kechikdi) / (keldi + kechikdi + kelmadi); belgilanmagan — None.
    attendance: int | None
    # Bugungi kunlik testni tugatganlar; bugun test yo'q — None.
    daily_done: int | None
    # Tekshirilmagan uy vazifalari va baholanmagan imtihon javoblari.
    unchecked: int
    url: str


def groups_overview(viewer: User, now: datetime | None = None) -> list[GroupRow]:
    """O'qiyotgan va yig'ilayotgan guruhlar: avval o'qiyotganlari."""
    now = now or timezone.now()
    groups = list(
        StudyGroup.objects.filter(status__in=[StudyGroup.Status.ACTIVE, StudyGroup.Status.FORMING])
        .select_related("course", "teacher")
        .order_by("status", "name")  # ACTIVE < FORMING
    )
    ids = [group.pk for group in groups]
    members: dict[int, list[int]] = {}
    for group_id, user_id in Enrollment.objects.filter(
        group_id__in=ids, status=Enrollment.Status.ACTIVE
    ).values_list("group_id", "user_id"):
        members.setdefault(group_id, []).append(user_id)
    attendance = {
        row["live_lesson__group_id"]: round(row["came"] * 100 / row["total"])
        for row in Attendance.objects.filter(
            live_lesson__group_id__in=ids,
            live_lesson__canceled_at__isnull=True,
            live_lesson__starts_at__gte=now - timedelta(days=ATTENDANCE_DAYS),
            live_lesson__starts_at__lte=now,
            status__in=[
                Attendance.Status.PRESENT,
                Attendance.Status.LATE,
                Attendance.Status.ABSENT,
            ],
        )
        .values("live_lesson__group_id")
        .annotate(came=Count("pk", filter=~Q(status=Attendance.Status.ABSENT)), total=Count("pk"))
    }
    today = timezone.localdate(now)
    tested = set(
        DailyTest.objects.filter(group_id__in=ids, day=today).values_list("group_id", flat=True)
    )
    done = dict(
        DailyAttempt.objects.filter(
            test__group_id__in=ids, test__day=today, finished_at__isnull=False
        )
        .values("test__group_id")
        .annotate(count=Count("pk"))
        .values_list("test__group_id", "count")
    )
    rows = []
    for group in groups:
        people = members.get(group.pk, [])
        homework = Submission.objects.filter(
            status=Submission.Status.SUBMITTED,
            student_id__in=people,
            assignment__lesson__module__course_id=group.course_id,
        ).count()
        answers = TaskAnswer.objects.filter(
            score__isnull=True, student_id__in=people, task__exam__course_id=group.course_id
        ).count()
        rows.append(
            GroupRow(
                group=group,
                students=len(people),
                attendance=attendance.get(group.pk),
                daily_done=done.get(group.pk, 0) if group.pk in tested else None,
                unchecked=homework + answers,
                url=(
                    site_link(viewer, f"/dashboard/teaching/{group.pk}")
                    if can_open_group(viewer, group)
                    else ""
                ),
            )
        )
    return rows


@dataclass(frozen=True)
class ExamRow:
    exam: Exam
    # open — hamma uchun ochiq; extended — faqat alohida muddat olganlarga; closed — yopilgan
    state: str
    students: int
    tested: int
    to_grade: int
    passed: int
    url: str


def exams_overview(viewer: User, now: datetime | None = None) -> list[ExamRow]:
    """Ochiq, alohida muddat bilan ochiq va oxirgi 2 haftada yopilgan imtihonlar; baholanmagan
    javobi borlari — har doim."""
    now = now or timezone.now()
    recent = now - EXAM_RECENT
    found = list(
        Exam.objects.filter(status=Exam.Status.READY, opens_at__lte=now)
        .filter(
            Q(closes_at__gte=recent)
            | Q(extensions__until__gte=recent)
            | Q(tasks__answers__score__isnull=True, tasks__answers__isnull=False)
        )
        .select_related("course")
        .distinct()
        .order_by("-closes_at", "-pk")[:MAX_EXAMS]
    )
    extended = set(
        Exam.objects.filter(
            pk__in=[exam.pk for exam in found], extensions__until__gt=now
        ).values_list("pk", flat=True)
    )
    passed = dict(
        ExamResult.objects.filter(exam__in=found, passed=True, final_at__isnull=False)
        .values("exam_id")
        .annotate(count=Count("pk"))
        .values_list("exam_id", "count")
    )
    rows = []
    for exam in found:
        card = payloads.teacher_card(exam, viewer)
        state = "open" if now < exam.closes_at else "extended" if exam.pk in extended else "closed"
        rows.append(
            ExamRow(
                exam=exam,
                state=state,
                students=card["students"],
                tested=card["tested"],
                to_grade=card["to_grade"],
                passed=passed.get(exam.pk, 0),
                url=(
                    site_link(viewer, f"/dashboard/teaching/exams/{exam.pk}")
                    if exams.can_manage(viewer, exam)
                    else ""
                ),
            )
        )
    return rows
