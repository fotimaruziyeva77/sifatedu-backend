"""Test API: urinishni boshlash (yoki davom ettirish), javob berish, yakunlash."""

from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.learning import access
from apps.live.gates import tasks_open
from apps.users.models import User

from . import services
from .models import Attempt, Quiz
from .serializers import (
    QuizAnswerSerializer,
    QuizAttemptSerializer,
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
