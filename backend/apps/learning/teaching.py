"""O'qituvchi kabineti: o'z guruhlari va o'quvchilarining progressi.

O'qituvchi faqat o'ziga biriktirilgan guruhlarni ko'radi. O'quvchi haqida — ismi, telefoni va
o'qish holati (TZ 3.2: "o'z guruhlari, cheklangan").
"""

from datetime import timedelta
from typing import Any

from django.db.models import Avg, Case, Count, IntegerField, Max, Q, Value, When
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Lesson
from apps.live.models import Attendance, LiveLesson
from apps.live.services import attendance_rates
from apps.quizzes.services import group_quiz_stats
from apps.users.roles import Role, has_role

from .models import Enrollment, LessonProgress, StudyGroup

# Shuncha kun dars ko'rmagan o'quvchi "faol emas" deb belgilanadi — o'qituvchi bog'lanadi.
INACTIVE_AFTER = timedelta(days=7)


class IsTeacher(BasePermission):
    message = "Bu bo'lim faqat o'qituvchilar uchun."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return has_role(request.user, Role.TEACHER)


class TeacherStudentSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    phone = serializers.CharField()
    avatar = serializers.CharField(allow_blank=True)
    completed = serializers.IntegerField()
    total = serializers.IntegerField()
    percent = serializers.IntegerField()
    last_activity = serializers.DateTimeField(allow_null=True)
    inactive = serializers.BooleanField(help_text="7 kundan beri dars ko'rmagan yoki boshlamagan.")
    study_format = serializers.CharField()
    access_until = serializers.DateTimeField(allow_null=True)
    active = serializers.BooleanField(help_text="Kursga kirish ochiq (to'lov muddati o'tmagan).")
    homework_accepted = serializers.IntegerField(help_text="Qabul qilingan uy vazifalari.")
    homework_pending = serializers.IntegerField(help_text="Tekshirilishi kutilayotganlari.")
    homework_average = serializers.IntegerField(
        allow_null=True, help_text="Qabul qilinganlarning o'rtacha bahosi."
    )
    quiz_average = serializers.IntegerField(
        allow_null=True, help_text="Ishlangan testlar bo'yicha eng yaxshi natijalar o'rtachasi (%)."
    )
    quiz_passed = serializers.IntegerField(help_text="O'tilgan testlar soni.")
    attendance_rate = serializers.IntegerField(
        allow_null=True, help_text="Oxirgi 30 kun davomati (%): kelgan va kechikkanlar."
    )


class TeacherGroupSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    course_icon = serializers.CharField()
    study_format = serializers.CharField()
    schedule = serializers.CharField(allow_blank=True)
    starts_on = serializers.DateField(allow_null=True)
    status = serializers.ChoiceField(choices=StudyGroup.Status.choices)
    students_count = serializers.IntegerField()
    average_percent = serializers.IntegerField()


class GroupLessonSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    title = serializers.CharField(allow_blank=True)
    starts_at = serializers.DateTimeField()
    kind = serializers.ChoiceField(choices=LiveLesson.Kind.choices)
    canceled = serializers.BooleanField()
    marked = serializers.IntegerField(help_text="Davomati belgilanganlar.")
    came = serializers.IntegerField(help_text="Kelgan va kechikkanlar.")


class TeacherGroupDetailSerializer(TeacherGroupSerializer):
    students = TeacherStudentSerializer(many=True)
    lessons = GroupLessonSerializer(
        many=True, help_text="Oxirgi 5 ta o'tgan va yaqin 5 ta jonli dars (vaqt bo'yicha)."
    )


def group_students(group: StudyGroup) -> list[dict[str, Any]]:
    """Guruh o'quvchilari progressi bilan; orqada qolganlar birinchi (yordam kerak bo'lganlar)."""
    enrollments = list(
        group.enrollments.filter(status=Enrollment.Status.ACTIVE).select_related("user")
    )
    user_ids = [enrollment.user_id for enrollment in enrollments]
    lessons = Lesson.objects.filter(module__course_id=group.course_id)
    total = lessons.count()
    stats = {
        row["user_id"]: row
        for row in LessonProgress.objects.filter(user_id__in=user_ids, lesson__in=lessons)
        .values("user_id")
        .annotate(
            done=Count("pk", filter=Q(completed_at__isnull=False)),
            last=Max("updated_at"),
        )
    }
    homework = homework_stats(user_ids, group.course_id)
    quizzes = group_quiz_stats(user_ids, group.course_id)
    attendance = attendance_rates(user_ids, group.pk)
    stale_before = timezone.now() - INACTIVE_AFTER
    students = []
    for enrollment in enrollments:
        user = enrollment.user
        row = stats.get(user.pk, {})
        completed = int(row.get("done", 0))
        students.append(
            {
                "id": user.pk,
                "name": user.get_full_name() or user.phone,
                "phone": user.phone,
                "avatar": user.avatar.url if user.avatar else "",
                "completed": completed,
                "total": total,
                "percent": round(completed * 100 / total) if total else 0,
                "last_activity": row.get("last"),
                "inactive": row.get("last") is None or row["last"] < stale_before,
                "study_format": enrollment.study_format,
                "access_until": enrollment.expires_at,
                "active": enrollment.is_open,
                **homework.get(
                    user.pk,
                    {"homework_accepted": 0, "homework_pending": 0, "homework_average": None},
                ),
                **quizzes.get(user.pk, {"quiz_average": None, "quiz_passed": 0}),
                "attendance_rate": attendance.get(user.pk),
            }
        )
    return sorted(students, key=lambda student: (student["percent"], student["name"]))


def homework_stats(user_ids: list[int], course_id: int) -> dict[int, dict[str, Any]]:
    """Har bir o'quvchining shu kursdagi uy vazifalari: qabul qilingan, kutayotgan, o'rtacha."""
    from apps.homework.models import Submission

    rows = (
        Submission.objects.filter(
            student_id__in=user_ids, assignment__lesson__module__course_id=course_id
        )
        .values("student_id")
        .annotate(
            accepted=Count("pk", filter=Q(status=Submission.Status.ACCEPTED)),
            pending=Count("pk", filter=Q(status=Submission.Status.SUBMITTED)),
            average=Avg("score", filter=Q(status=Submission.Status.ACCEPTED)),
        )
    )
    return {
        row["student_id"]: {
            "homework_accepted": row["accepted"],
            "homework_pending": row["pending"],
            "homework_average": round(row["average"]) if row["average"] is not None else None,
        }
        for row in rows
    }


def group_card(group: StudyGroup, students: list[dict[str, Any]]) -> dict[str, Any]:
    course = group.course
    return {
        "id": group.pk,
        "name": group.name,
        "course_title": course.title,
        "course_slug": course.slug,
        "course_icon": course.icon,
        "study_format": group.study_format,
        "schedule": group.schedule,
        "starts_on": group.starts_on,
        "status": group.status,
        "students_count": len(students),
        "average_percent": (
            round(sum(student["percent"] for student in students) / len(students))
            if students
            else 0
        ),
    }


def teacher_groups(user: Any) -> Any:
    # Avval o'qiyotgan guruhlar, keyin yig'ilayotganlar, oxirida tugaganlar.
    stage = Case(
        When(status=StudyGroup.Status.ACTIVE, then=Value(0)),
        When(status=StudyGroup.Status.FORMING, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    return (
        StudyGroup.objects.filter(teacher=user)
        .select_related("course")
        .order_by(stage, "-starts_on", "name")
    )


class TeacherGroupsView(APIView):
    """O'qituvchining guruhlari: holati, o'quvchilar soni va o'rtacha progress."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses=TeacherGroupSerializer(many=True), tags=["teacher"])
    def get(self, request: Request) -> Response:
        cards = [group_card(group, group_students(group)) for group in teacher_groups(request.user)]
        return Response(cards)


class TeacherGroupView(APIView):
    """Guruh sahifasi: o'quvchilar ro'yxati va har birining progressi."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses=TeacherGroupDetailSerializer, tags=["teacher"])
    def get(self, request: Request, pk: int) -> Response:
        # Boshqa o'qituvchining guruhi — 404: bunday guruh borligini ham ochib bermaydi.
        group = get_object_or_404(teacher_groups(request.user), pk=pk)
        students = group_students(group)
        return Response(
            {**group_card(group, students), "students": students, "lessons": group_lessons(group)}
        )


def group_lessons(group: StudyGroup) -> list[dict[str, Any]]:
    """Guruh sahifasi uchun: oxirgi 5 ta o'tgan va yaqin 5 ta dars."""
    now = timezone.now()
    lessons = LiveLesson.objects.filter(group=group).select_related("topic")
    counted = lessons.annotate(
        marked=Count("attendance", filter=~Q(attendance__status="")),
        came=Count(
            "attendance",
            filter=Q(attendance__status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE]),
        ),
    )
    past = list(counted.filter(starts_at__lt=now).order_by("-starts_at")[:5])
    upcoming = list(counted.filter(starts_at__gte=now).order_by("starts_at")[:5])
    return [
        {
            "id": lesson.pk,
            "title": lesson.title or (str(lesson.topic.title) if lesson.topic else ""),
            "starts_at": lesson.starts_at,
            "kind": lesson.kind,
            "canceled": lesson.is_canceled,
            "marked": lesson.marked,  # type: ignore[attr-defined]
            "came": lesson.came,  # type: ignore[attr-defined]
        }
        for lesson in [*reversed(past), *upcoming]
    ]
