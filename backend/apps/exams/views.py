"""Oylik imtihon API: o'quvchi (test, amaliy topshiriqlar, natija) va o'qituvchi (baholash)."""

from datetime import timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.catalog.scope import teacher_courses
from apps.homework import files
from apps.learning.models import StudyGroup
from apps.users.models import User
from apps.users.roles import sees_all

from . import payloads, services
from .models import Exam, ExamAttempt, ExamTask, TaskAnswer
from .serializers import (
    ExamAnswerSerializer,
    ExamAttemptSerializer,
    ExamCardSerializer,
    ExamDetailSerializer,
    ExamFinishSerializer,
    ExamSavedSerializer,
    ExtensionSerializer,
    GradeSerializer,
    TaskSubmitSerializer,
    TeacherExamDetailSerializer,
    TeacherExamSerializer,
)

TEACHER_MONTHS = 6


def exam_error(exc: services.ExamError) -> ValidationError:
    return ValidationError({"non_field_errors": [str(exc)]})


def visible_exam(user: User, pk: int) -> Exam:
    """O'quvchiga ko'rinadigan imtihon: qatnashuvchi yoki unda faollik bor."""
    exam = get_object_or_404(Exam.objects.select_related("course"), pk=pk, status=Exam.Status.READY)
    active = (
        ExamAttempt.objects.filter(exam=exam, student=user).exists()
        or TaskAnswer.objects.filter(task__exam=exam, student=user).exists()
    )
    if not (active or services.is_participant(exam, user)):
        raise NotFound
    return exam


class ExamListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ExamCardSerializer(many=True)}, tags=["exams"])
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        now = timezone.now()
        return Response([payloads.card(exam, user, now=now) for exam in services.exams_for(user)])


class ExamDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ExamDetailSerializer}, tags=["exams"])
    def get(self, request: Request, pk: int) -> Response:
        user: User = request.user  # type: ignore[assignment]
        return Response(payloads.detail(visible_exam(user, pk), user))


class ExamTestView(APIView):
    """Testni boshlash yoki davom ettirish (bitta urinish; vaqt serverda)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "quiz"

    @extend_schema(request=None, responses={200: ExamAttemptSerializer}, tags=["exams"])
    def post(self, request: Request, pk: int) -> Response:
        user: User = request.user  # type: ignore[assignment]
        exam = visible_exam(user, pk)
        try:
            attempt = services.start_test(exam, user)
        except services.ExamError as exc:
            raise exam_error(exc) from exc
        return Response(services.attempt_payload(attempt))


class ExamAttemptView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "quiz"

    def attempt(self, request: Request, pk: int) -> ExamAttempt:
        return get_object_or_404(ExamAttempt, pk=pk, student_id=request.user.pk)


class ExamAttemptAnswerView(ExamAttemptView):
    """Javob saqlanadi; to'g'ri yoki noto'g'riligi imtihon yopilgach."""

    @extend_schema(
        request=ExamAnswerSerializer, responses={200: ExamSavedSerializer}, tags=["exams"]
    )
    def post(self, request: Request, pk: int) -> Response:
        attempt = self.attempt(request, pk)
        serializer = ExamAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data
        try:
            saved = services.answer_test(attempt, data["question"], data["response"])
        except services.ExamError as exc:
            raise exam_error(exc) from exc
        return Response(saved)


class ExamAttemptFinishView(ExamAttemptView):
    @extend_schema(request=None, responses={200: ExamFinishSerializer}, tags=["exams"])
    def post(self, request: Request, pk: int) -> Response:
        attempt = services.finish_test(self.attempt(request, pk))
        return Response({"score": attempt.score or 0})


class TaskAnswerView(APIView):
    """Amaliy topshiriq javobi (multipart): izoh, kod, havola va 5 tagacha fayl."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "homework"

    @extend_schema(
        request={"multipart/form-data": TaskSubmitSerializer},
        responses={201: ExamDetailSerializer},
        tags=["exams"],
    )
    def post(self, request: Request, pk: int) -> Response:
        user: User = request.user  # type: ignore[assignment]
        task = get_object_or_404(ExamTask.objects.select_related("exam"), pk=pk)
        visible_exam(user, task.exam_id)
        serializer = TaskSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            checked = files.check(request.FILES.getlist("files"))
            services.submit_task(
                task,
                user,
                text=data["text"],
                code=data["code"],
                language=data["language"],
                link=data["link"],
                files=checked,
            )
        except files.FileRejected as exc:
            raise ValidationError({"files": [str(exc)]}) from exc
        except services.ExamError as exc:
            raise exam_error(exc) from exc
        return Response(payloads.detail(task.exam, user), status=201)


# --- O'qituvchi ---


def managed_exams(user: Any) -> Any:
    since = timezone.localdate() - timedelta(days=31 * TEACHER_MONTHS)
    exams = Exam.objects.select_related("course").filter(month__gte=since)
    if sees_all(user):
        return exams
    courses = teacher_courses(user).values("pk")
    groups = StudyGroup.objects.filter(teacher=user).values("course_id")
    return exams.filter(Q(course__in=courses) | Q(course__in=groups))


def managed_exam(user: Any, pk: int) -> Exam:
    exam = get_object_or_404(Exam.objects.select_related("course"), pk=pk)
    if not services.can_manage(user, exam):
        raise NotFound
    return exam


class TeacherExamListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: TeacherExamSerializer(many=True)}, tags=["exams"])
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        if not (sees_all(user) or user.is_staff):
            raise PermissionDenied
        exams = managed_exams(user).order_by("-month", "course__order")
        return Response([payloads.teacher_card(exam, user) for exam in exams])


class TeacherExamDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: TeacherExamDetailSerializer}, tags=["exams"])
    def get(self, request: Request, pk: int) -> Response:
        user: User = request.user  # type: ignore[assignment]
        return Response(payloads.teacher_detail(managed_exam(user, pk), user))


class TeacherGradeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=GradeSerializer, responses={200: TeacherExamDetailSerializer}, tags=["exams"]
    )
    def post(self, request: Request, pk: int) -> Response:
        user: User = request.user  # type: ignore[assignment]
        answer = get_object_or_404(
            TaskAnswer.objects.select_related("task__exam__course", "student"), pk=pk
        )
        exam = managed_exam(user, answer.task.exam_id)
        if answer.student_id not in {person.pk for person in services.students_of(user, exam)}:
            raise NotFound
        serializer = GradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.grade_task(
                answer,
                user,
                score=serializer.validated_data["score"],
                feedback=serializer.validated_data["feedback"],
            )
        except services.ExamError as exc:
            raise exam_error(exc) from exc
        return Response(payloads.teacher_detail(exam, user))


class TeacherExtensionView(APIView):
    """Kelolmagan o'quvchiga alohida muddat."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ExtensionSerializer, responses={200: TeacherExamDetailSerializer}, tags=["exams"]
    )
    def put(self, request: Request, pk: int) -> Response:
        user: User = request.user  # type: ignore[assignment]
        exam = managed_exam(user, pk)
        serializer = ExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = next(
            (
                person
                for person in services.students_of(user, exam)
                if person.pk == serializer.validated_data["student"]
            ),
            None,
        )
        if student is None:
            raise NotFound
        try:
            services.grant_extension(exam, student, serializer.validated_data["until"], user)
        except services.ExamError as exc:
            raise exam_error(exc) from exc
        return Response(payloads.teacher_detail(exam, user))
