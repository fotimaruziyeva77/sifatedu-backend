"""Test API: urinishni boshlash (yoki davom ettirish), javob berish, yakunlash."""

from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.learning import access
from apps.live.gates import tasks_open
from apps.users.models import User

from . import drafts, services
from .models import Attempt, Quiz, QuizDraft
from .parser import ParseError
from .serializers import (
    QuizAnswerSerializer,
    QuizAttemptSerializer,
    QuizDraftCreateSerializer,
    QuizDraftPublishedSerializer,
    QuizDraftPublishSerializer,
    QuizDraftSerializer,
    QuizFinishSerializer,
    QuizResultSerializer,
)


def quiz_error(exc: services.QuizError) -> ValidationError:
    return ValidationError({"non_field_errors": [str(exc)]})


class QuizStartView(APIView):
    """Tugallanmagan urinish bo'lsa — o'sha (javoblari bilan), aks holda yangisi.
    `?new=1` — yangisini boshlash."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "quiz"

    @extend_schema(
        request=None,
        parameters=[OpenApiParameter("new", bool, required=False)],
        responses={200: QuizAttemptSerializer},
        tags=["quizzes"],
    )
    def post(self, request: Request, pk: int) -> Response:
        quiz = get_object_or_404(Quiz.objects.select_related("lesson__module__course"), pk=pk)
        if not access.can_open_lesson(request.user, quiz.lesson):
            raise PermissionDenied("Bu dars sizga ochiq emas.")
        if not tasks_open(request.user, quiz.lesson):
            raise PermissionDenied("Bu darsning testi ustoz darsni o'tgach ochiladi.")
        user: User = request.user  # type: ignore[assignment]
        try:
            fresh = request.query_params.get("new", "").lower() in ("1", "true")
            attempt = services.start(quiz, user, fresh=fresh)
        except services.QuizError as exc:
            raise quiz_error(exc) from exc
        return Response(services.attempt_payload(attempt))


class AttemptView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "quiz"

    def attempt(self, request: Request, pk: int) -> Attempt:
        # Boshqa o'quvchining urinishi — 404.
        return get_object_or_404(
            Attempt.objects.select_related("quiz"), pk=pk, student_id=request.user.pk
        )


class AttemptAnswerView(AttemptView):
    """Bitta savolga javob: darhol natija, to'g'ri javob va izoh."""

    @extend_schema(
        request=QuizAnswerSerializer, responses={200: QuizResultSerializer}, tags=["quizzes"]
    )
    def post(self, request: Request, pk: int) -> Response:
        attempt = self.attempt(request, pk)
        serializer = QuizAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data
        try:
            result = services.answer(attempt, data["question"], data["response"])
        except services.QuizError as exc:
            raise quiz_error(exc) from exc
        return Response(result)


class AttemptFinishView(AttemptView):
    """Yakunlash: foiz, yulduzlar, o'tdimi va eng yaxshi natija."""

    @extend_schema(request=None, responses={200: QuizFinishSerializer}, tags=["quizzes"])
    def post(self, request: Request, pk: int) -> Response:
        attempt = self.attempt(request, pk)
        return Response(services.finish(attempt), status=status.HTTP_200_OK)


# --- Qo'llanmadan AI test (o'qituvchi) ---


def managed_draft(user: Any, pk: int) -> QuizDraft:
    from apps.live import services as live

    draft = get_object_or_404(
        QuizDraft.objects.select_related("lesson", "live_lesson__group"), pk=pk
    )
    if draft.live_lesson is None or not live.can_manage(user, draft.live_lesson):
        raise NotFound
    return draft


class TeacherDraftCreateView(APIView):
    """Jonli darsga qo'llanma yuklanadi — AI test tuzadi (`ai` navbati, 30–90 s)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": QuizDraftCreateSerializer},
        responses={201: QuizDraftSerializer},
        tags=["teacher"],
    )
    def post(self, request: Request, pk: int) -> Response:
        from apps.catalog.models import Lesson
        from apps.live import services as live
        from apps.live.models import LiveLesson

        lesson = get_object_or_404(LiveLesson.objects.select_related("group__course"), pk=pk)
        if not live.can_manage(request.user, lesson):
            raise NotFound
        serializer = QuizDraftCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        topic: Lesson | None = None
        if data.get("lesson"):
            topic = get_object_or_404(
                Lesson.objects.select_related("module"),
                pk=data["lesson"],
                module__course_id=lesson.group.course_id,
            )
        try:
            draft = drafts.create(
                lesson,
                by=request.user,
                upload=data["file"],
                topic=topic,
                new_title=data.get("new_title", ""),
            )
        except drafts.DraftError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(drafts.payload(draft), status=status.HTTP_201_CREATED)


class TeacherDraftView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: QuizDraftSerializer}, tags=["teacher"])
    def get(self, request: Request, pk: int) -> Response:
        return Response(drafts.payload(drafts.expire(managed_draft(request.user, pk))))


class TeacherDraftPublishView(APIView):
    """Tekshirilgan savollar mavzu testiga qo'shiladi; mavzu guruhda «o'tildi» bo'ladi."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=QuizDraftPublishSerializer,
        responses={200: QuizDraftPublishedSerializer},
        tags=["teacher"],
    )
    def post(self, request: Request, pk: int) -> Response:
        draft = managed_draft(request.user, pk)
        serializer = QuizDraftPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = drafts.publish(
                draft,
                by=request.user,
                text=serializer.validated_data["text"],
                share_file=serializer.validated_data["share_file"],
            )
        except ParseError as exc:
            raise ValidationError({"text": exc.errors}) from exc
        except drafts.DraftError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        draft.refresh_from_db()
        return Response({"draft": drafts.payload(draft), **result})
