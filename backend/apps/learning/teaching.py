"""O'qituvchi kabineti: o'z guruhlari va o'quvchilarining progressi.

O'qituvchi faqat o'ziga biriktirilgan guruhlarni ko'radi, admin va menejer — hammasini
(`manages_groups`). O'quvchi haqida — ismi, telefoni va o'qish holati (TZ 3.2: "o'z guruhlari,
cheklangan"). Guruhga o'quvchi qo'shadi va chiqaradi, haftalik dars jadvalini kiritadi (`roster`).
"""

from datetime import timedelta
from typing import Any

from django.db.models import Avg, Case, Count, IntegerField, Max, Q, Value, When
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bot import links
from apps.catalog.models import Lesson
from apps.live.models import Attendance, LiveLesson, ScheduleSlot
from apps.live.services import attendance_rates
from apps.quizzes.services import group_quiz_stats
from apps.users.roles import Role, has_role, manages_groups

from . import roster
from .models import Enrollment, LessonProgress, StudyGroup

# Shuncha kun dars ko'rmagan o'quvchi "faol emas" deb belgilanadi — o'qituvchi bog'lanadi.
INACTIVE_AFTER = timedelta(days=7)


class IsTeacher(BasePermission):
    message = "Bu bo'lim o'qituvchi, menejer va admin uchun."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return has_role(request.user, Role.TEACHER) or manages_groups(request.user)


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
    teacher_name = serializers.CharField(help_text="Guruh o'qituvchisi.")
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


class SlotSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    weekday = serializers.IntegerField(help_text="0 — dushanba … 6 — yakshanba.")
    starts_at = serializers.TimeField(format="%H:%M")
    duration_min = serializers.IntegerField()


class TeacherGroupDetailSerializer(TeacherGroupSerializer):
    students = TeacherStudentSerializer(many=True)
    lessons = GroupLessonSerializer(
        many=True, help_text="Oxirgi 5 ta o'tgan va yaqin 5 ta jonli dars (vaqt bo'yicha)."
    )
    slots = SlotSerializer(many=True, help_text="Haftalik dars jadvali.")
    bot_url = serializers.CharField(
        allow_blank=True, help_text="Bot havolasi: yangi o'quvchi shu raqam bilan kirsin."
    )


class AddStudentSerializer(serializers.Serializer[dict[str, Any]]):
    phone = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False, default="")
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False, default="")


class AddedStudentSerializer(serializers.Serializer[dict[str, Any]]):
    group = TeacherGroupDetailSerializer()
    name = serializers.CharField()
    created = serializers.BooleanField(help_text="Yangi akkaunt: o'quvchi hali botga kirmagan.")
    moved_from = serializers.CharField(
        allow_blank=True, help_text="Boshqa guruhdan o'tkazildi — eski guruh nomi."
    )


class SlotInputSerializer(serializers.Serializer[dict[str, Any]]):
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    starts_at = serializers.TimeField()
    duration_min = serializers.IntegerField(min_value=15, max_value=480, default=90)


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
        "teacher_name": group.teacher.get_full_name() or group.teacher.phone,
        "students_count": len(students),
        "average_percent": (
            round(sum(student["percent"] for student in students) / len(students))
            if students
            else 0
        ),
    }


def teacher_groups(user: Any) -> Any:
    """O'qituvchiga — o'z guruhlari, admin va menejerga — hammasi."""
    # Avval o'qiyotgan guruhlar, keyin yig'ilayotganlar, oxirida tugaganlar.
    stage = Case(
        When(status=StudyGroup.Status.ACTIVE, then=Value(0)),
        When(status=StudyGroup.Status.FORMING, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    groups = (
        StudyGroup.objects.all()
        if manages_groups(user)
        else StudyGroup.objects.filter(teacher=user)
    )
    return groups.select_related("course", "teacher").order_by(stage, "-starts_on", "name")


class TeacherGroupsView(APIView):
    """O'qituvchining guruhlari (admin va menejerga — hammasi): holati, o'quvchilar soni va
    o'rtacha progress."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses=TeacherGroupSerializer(many=True), tags=["teacher"])
    def get(self, request: Request) -> Response:
        cards = [group_card(group, group_students(group)) for group in teacher_groups(request.user)]
        return Response(cards)


def my_group(user: Any, pk: int) -> StudyGroup:
    # O'qituvchiga boshqa o'qituvchining guruhi — 404: bunday guruh borligini ham ochib bermaydi.
    return get_object_or_404(teacher_groups(user), pk=pk)


def group_detail(group: StudyGroup) -> dict[str, Any]:
    students = group_students(group)
    slots = ScheduleSlot.objects.filter(group=group).order_by("weekday", "starts_at")
    return {
        **group_card(group, students),
        "students": students,
        "lessons": group_lessons(group),
        "slots": [
            {
                "id": slot.pk,
                "weekday": slot.weekday,
                "starts_at": f"{slot.starts_at:%H:%M}",
                "duration_min": slot.duration_min,
            }
            for slot in slots
        ],
        "bot_url": links.bot_url() or "",
    }


def roster_error(exc: roster.RosterError) -> ValidationError:
    return ValidationError({"non_field_errors": [str(exc)]})


class TeacherGroupView(APIView):
    """Guruh sahifasi: o'quvchilar ro'yxati, progress, darslar va haftalik jadval."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(responses=TeacherGroupDetailSerializer, tags=["teacher"])
    def get(self, request: Request, pk: int) -> Response:
        return Response(group_detail(my_group(request.user, pk)))


class TeacherGroupStudentsView(APIView):
    """Guruhga o'quvchi qo'shish (telefon va ism bilan)."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(
        request=AddStudentSerializer, responses={201: AddedStudentSerializer}, tags=["teacher"]
    )
    def post(self, request: Request, pk: int) -> Response:
        group = my_group(request.user, pk)
        serializer = AddStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            added = roster.add_student(group, **serializer.validated_data)
        except roster.RosterError as exc:
            raise roster_error(exc) from exc
        user = added.user
        return Response(
            {
                "group": group_detail(group),
                "name": user.get_full_name() or user.phone,
                "created": added.created,
                "moved_from": added.moved_from,
            },
            status=201,
        )


class TeacherGroupStudentView(APIView):
    """Guruhdan chiqarish: kursga kirish yopiladi, tarix qoladi."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(request=None, responses={200: TeacherGroupDetailSerializer}, tags=["teacher"])
    def delete(self, request: Request, pk: int, user_id: int) -> Response:
        group = my_group(request.user, pk)
        try:
            roster.remove_student(group, user_id)
        except roster.RosterError as exc:
            raise roster_error(exc) from exc
        return Response(group_detail(group))


class TeacherGroupSlotsView(APIView):
    """Haftalik jadvalga dars qo'shish: darslar 14 kun oldinga o'zi yaratiladi."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(
        request=SlotInputSerializer, responses={201: TeacherGroupDetailSerializer}, tags=["teacher"]
    )
    def post(self, request: Request, pk: int) -> Response:
        group = my_group(request.user, pk)
        serializer = SlotInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            roster.add_slot(group, **serializer.validated_data)
        except roster.RosterError as exc:
            raise roster_error(exc) from exc
        return Response(group_detail(group), status=201)


class TeacherGroupSlotView(APIView):
    """Jadvaldan darsni olib tashlash: kelgusi belgilanmagan darslar ham o'chadi."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(request=None, responses={200: TeacherGroupDetailSerializer}, tags=["teacher"])
    def delete(self, request: Request, pk: int, slot_id: int) -> Response:
        group = my_group(request.user, pk)
        try:
            roster.remove_slot(group, slot_id)
        except roster.RosterError as exc:
            raise roster_error(exc) from exc
        return Response(group_detail(group))


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
