"""Uy vazifalari API: o'quvchi javob yuboradi, o'qituvchi tekshiradi."""

from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.learning import access
from apps.learning.models import Enrollment, StudyGroup
from apps.live.gates import tasks_open
from apps.users.models import User
from apps.users.roles import Role, has_role

from . import files, services
from .models import Assignment, Submission
from .serializers import (
    HomeworkSerializer,
    MyHomeworkItemSerializer,
    ReviewDecisionSerializer,
    ReviewDetailSerializer,
    ReviewListSerializer,
    SubmitSerializer,
)

# "Tekshirilgan" yorlig'ida shuncha kunlik javoblar.
REVIEWED_DAYS = 30
LIST_LIMIT = 200


class HomeworkSubmitView(APIView):
    """Javob yuborish (multipart): izoh, kod, havola va 5 tagacha fayl."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "homework"

    @extend_schema(
        request={"multipart/form-data": SubmitSerializer},
        responses={201: HomeworkSerializer},
        tags=["homework"],
    )
    def post(self, request: Request, pk: int) -> Response:
        assignment = get_object_or_404(
            Assignment.objects.select_related("lesson", "lesson__module__course"), pk=pk
        )
        if not access.can_open_lesson(request.user, assignment.lesson):
            raise PermissionDenied("Bu dars sizga ochiq emas.")
        if not tasks_open(request.user, assignment.lesson):
            raise PermissionDenied("Bu darsning vazifasi ustoz darsni o'tgach ochiladi.")
        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            checked = files.check(request.FILES.getlist("files"))
            services.submit(
                assignment,
                request.user,  # type: ignore[arg-type]
                text=data["text"],
                code=data["code"],
                language=data["language"],
                link=data["link"],
                files=checked,
            )
        except files.FileRejected as exc:
            raise ValidationError({"files": [str(exc)]}) from exc
        except services.HomeworkError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        payload = services.homework_payload(assignment.lesson, request.user)
        return Response(payload, status=status.HTTP_201_CREATED)


class SubmissionWithdrawView(APIView):
    """Hali tekshirilmagan javobni qaytarib olish (keyin yangisini yuborish mumkin)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None}, tags=["homework"])
    def delete(self, request: Request, pk: int) -> Response:
        submission = get_object_or_404(Submission, pk=pk, student_id=request.user.pk)
        try:
            services.withdraw(submission)
        except services.HomeworkError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyHomeworkView(APIView):
    """ "Vazifalar" sahifasi: o'quvchining kurslaridagi vazifalar va holati."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MyHomeworkItemSerializer(many=True), tags=["homework"])
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        return Response(services.my_homework(user, access.enrolled_courses(user)))


# --- O'qituvchi ---


class IsReviewer(BasePermission):
    message = "Bu bo'lim o'qituvchilar uchun."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return has_role(request.user, Role.TEACHER) or services.can_review_all(request.user)


def group_names(submissions: Sequence[Submission]) -> dict[tuple[int, int], str]:
    """(o'quvchi, kurs) → guruh nomi: navbatda o'quvchi qaysi guruhdanligi ko'rinsin."""
    pairs = {(item.student_id, item.assignment.lesson.module.course_id) for item in submissions}
    rows = Enrollment.objects.filter(
        user_id__in={student for student, _course in pairs},
        course_id__in={course for _student, course in pairs},
        group__isnull=False,
    ).values_list("user_id", "course_id", "group__name")
    return {(user_id, course_id): name for user_id, course_id, name in rows}


def card(item: Submission, groups: dict[tuple[int, int], str]) -> dict[str, Any]:
    lesson = item.assignment.lesson
    return {
        "id": item.pk,
        "student_id": item.student_id,
        "student_name": item.student.get_full_name() or item.student.phone,
        "student_phone": item.student.phone,
        "group_name": groups.get((item.student_id, lesson.module.course_id), ""),
        "course_title": lesson.module.course.title,
        "lesson_title": lesson.title,
        "assignment_title": item.assignment.title,
        "attempt": item.attempt,
        "status": item.status,
        "late": item.late,
        "created_at": item.created_at,
        "score": item.score,
        "reviewed_at": item.reviewed_at,
        "preview": services.preview(item),
        "files_count": getattr(item, "files_count", 0),
    }


class ReviewListView(APIView):
    """Tekshirish navbati: kutayotganlar (eng eskisi tepada) yoki oxirgi 30 kunda
    tekshirilganlar."""

    permission_classes = [IsAuthenticated, IsReviewer]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, enum=["pending", "reviewed"], required=False),
            OpenApiParameter("group", int, required=False),
        ],
        responses=ReviewListSerializer,
        tags=["teacher"],
        operation_id="teacher_reviews_list",
    )
    def get(self, request: Request) -> Response:
        base = services.reviewable(request.user).annotate(files_count=Count("files"))
        pending = base.filter(status=Submission.Status.SUBMITTED)
        if request.query_params.get("status") == "reviewed":
            since = timezone.now() - timedelta(days=REVIEWED_DAYS)
            items = (
                base.exclude(status=Submission.Status.SUBMITTED)
                .filter(reviewed_at__gte=since)
                .order_by("-reviewed_at")
            )
        else:
            items = pending.order_by("created_at")
        group_id = request.query_params.get("group")
        if group_id and group_id.isdigit():
            members = Enrollment.objects.filter(group_id=int(group_id))
            items = items.filter(
                student_id__in=members.values("user_id"),
                assignment__lesson__module__course_id__in=members.values("course_id"),
            )
        rows = list(items[:LIST_LIMIT])
        groups = group_names(rows)
        user: User = request.user  # type: ignore[assignment]
        teacher_groups = (
            StudyGroup.objects.all()
            if services.can_review_all(user)
            else StudyGroup.objects.filter(teacher=user)
        )
        return Response(
            {
                "results": [card(item, groups) for item in rows],
                "groups": [{"id": g.pk, "name": g.name} for g in teacher_groups.order_by("name")],
                "pending": pending.count(),
            }
        )


class ReviewDetailView(APIView):
    """Javob sahifasi va qaror (qabul qilish — baho bilan, qaytarish — izoh bilan)."""

    permission_classes = [IsAuthenticated, IsReviewer]

    def submission(self, request: Request, pk: int) -> Submission:
        # Boshqa o'qituvchining o'quvchisi — 404: bunday javob borligini ham ochib bermaydi.
        return get_object_or_404(services.reviewable(request.user).prefetch_related("files"), pk=pk)

    def detail(self, request: Request, submission: Submission) -> dict[str, Any]:
        lesson = submission.assignment.lesson
        history = (
            Submission.objects.filter(
                assignment=submission.assignment,
                student=submission.student,
                attempt__lt=submission.attempt,
            )
            .select_related("reviewer")
            .prefetch_related("files")
            .order_by("-attempt")
        )
        upcoming = (
            services.reviewable(request.user)
            .filter(status=Submission.Status.SUBMITTED)
            .exclude(pk=submission.pk)
            .order_by("created_at")
            .values_list("pk", flat=True)
            .first()
        )
        submission.files_count = len(submission.files.all())  # type: ignore[attr-defined]
        return {
            **card(submission, group_names([submission])),
            "lesson_id": lesson.pk,
            "course_slug": lesson.module.course.slug,
            "instructions": submission.assignment.instructions,
            "deadline": submission.assignment.deadline,
            "submission": services.submission_payload(submission),
            "history": [services.submission_payload(item) for item in history],
            "next_id": upcoming,
        }

    @extend_schema(responses=ReviewDetailSerializer, tags=["teacher"])
    def get(self, request: Request, pk: int) -> Response:
        return Response(self.detail(request, self.submission(request, pk)))

    @extend_schema(
        request=ReviewDecisionSerializer, responses=ReviewDetailSerializer, tags=["teacher"]
    )
    def post(self, request: Request, pk: int) -> Response:
        submission = self.submission(request, pk)
        serializer = ReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            reviewed = services.review(
                submission,
                request.user,  # type: ignore[arg-type]
                accept=data["decision"] == "accept",
                score=data.get("score"),
                feedback=data["feedback"],
            )
        except services.HomeworkError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(self.detail(request, self.submission(request, reviewed.pk)))
