"""Jadval API: o'quvchi va o'qituvchining darslari, "Qo'shilish", davomat, bekor qilish, yozuv."""

from typing import Any

from django.http import Http404, HttpResponseRedirect
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Lesson
from apps.notifications.texts import locale_of
from apps.users.models import User

from . import services
from .models import GroupLesson, LiveLesson
from .serializers import (
    AttendanceSaveSerializer,
    CancelSerializer,
    CoverSerializer,
    LiveLessonSerializer,
    LiveUpdateSerializer,
    TeacherLiveSerializer,
)


def live_error(exc: services.LiveError) -> ValidationError:
    return ValidationError({"non_field_errors": [str(exc)]})


class ScheduleView(APIView):
    """O'quvchi — o'z guruhlari darslari, o'qituvchi — o'zi o'qitadigan guruhlar darslari.
    `when=upcoming` — 14 kun oldinga (ketayotgani ham), `past` — oxirgi 30 kun."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("when", str, enum=["upcoming", "past"], required=False)],
        responses={200: LiveLessonSerializer(many=True)},
        tags=["live"],
    )
    def get(self, request: Request) -> Response:
        upcoming = request.query_params.get("when", "upcoming") != "past"
        return Response(services.schedule(request.user, upcoming=upcoming))


class JoinView(APIView):
    """Onlayn darsga qo'shilish: havola faqat guruh a'zolariga, bosilgani davomatga yoziladi.
    Hozir qo'shilib bo'lmasa — jadval sahifasiga qaytaradi (`?closed=<id>`)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={302: OpenApiResponse(description="Meet/Zoom yoki jadval sahifasiga")},
        tags=["live"],
    )
    def get(self, request: Request, pk: int) -> HttpResponseRedirect:
        lesson = get_object_or_404(LiveLesson.objects.select_related("group"), pk=pk)
        user = request.user
        allowed = lesson.group_id in (
            services.student_group_ids(user) | services.teacher_group_ids(user)
        )
        if not allowed and not services.can_manage(user, lesson):
            raise Http404
        try:
            url = services.join(lesson, user)
        except services.LiveError:
            locale = locale_of(getattr(user, "locale", ""))
            return HttpResponseRedirect(f"/{locale}/dashboard/schedule?closed={lesson.pk}")
        return HttpResponseRedirect(url)


class TeacherLessonView(APIView):
    """O'qituvchi: dars, o'quvchilar ro'yxati va davomat; yozuv havolasi va izoh."""

    permission_classes = [IsAuthenticated]

    def lesson(self, request: Request, pk: int) -> LiveLesson:
        lesson = get_object_or_404(
            LiveLesson.objects.select_related("group__course", "group__teacher", "topic"), pk=pk
        )
        # Boshqa guruhning darsi — 404 (borligi ham bilinmasin).
        if not services.can_manage(request.user, lesson):
            raise Http404
        return lesson

    def payload(self, request: Request, lesson: LiveLesson) -> dict[str, Any]:
        now = timezone.now()
        data = services.lesson_payload(lesson, request.user, {}, now)
        return {
            **data,
            "recording_url": lesson.recording_url,
            "meet_url": lesson.meet_url,
            "can_mark": not lesson.is_canceled and now >= lesson.opens_at,
            "can_cancel": not lesson.is_canceled and now < lesson.starts_at,
            "students": services.roster(lesson),
            "topic_id": lesson.topic_id,
            "covered": lesson.topic_id is not None
            and GroupLesson.objects.filter(group=lesson.group, lesson_id=lesson.topic_id).exists(),
            "can_uncover": GroupLesson.objects.filter(live_lesson=lesson).exists(),
            "course_lessons": services.course_lessons(lesson),
        }

    @extend_schema(responses={200: TeacherLiveSerializer}, tags=["live"])
    def get(self, request: Request, pk: int) -> Response:
        return Response(self.payload(request, self.lesson(request, pk)))

    @extend_schema(
        request=LiveUpdateSerializer, responses={200: TeacherLiveSerializer}, tags=["live"]
    )
    def patch(self, request: Request, pk: int) -> Response:
        lesson = self.lesson(request, pk)
        serializer = LiveUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data
        if "notes" in data:
            lesson.notes = data["notes"]
            lesson.save(update_fields=["notes", "updated_at"])
        if "recording_url" in data and data["recording_url"] != lesson.recording_url:
            services.set_recording(lesson, data["recording_url"])
        return Response(self.payload(request, lesson))


class TeacherAttendanceView(TeacherLessonView):
    @extend_schema(
        request=AttendanceSaveSerializer, responses={200: TeacherLiveSerializer}, tags=["live"]
    )
    def put(self, request: Request, pk: int) -> Response:
        lesson = self.lesson(request, pk)
        serializer = AttendanceSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items: list[dict[str, Any]] = serializer.validated_data["items"]
        teacher: User = request.user  # type: ignore[assignment]
        try:
            services.save_attendance(
                lesson, teacher, {item["student"]: item["status"] for item in items}
            )
        except services.LiveError as exc:
            raise live_error(exc) from exc
        return Response(self.payload(request, lesson))


class TeacherCancelView(TeacherLessonView):
    @extend_schema(request=CancelSerializer, responses={200: TeacherLiveSerializer}, tags=["live"])
    def post(self, request: Request, pk: int) -> Response:
        lesson = self.lesson(request, pk)
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.cancel(lesson, serializer.validated_data["reason"], by=request.user)
        except services.LiveError as exc:
            raise live_error(exc) from exc
        return Response(self.payload(request, lesson))


class TeacherCoverView(TeacherLessonView):
    """ "Dars o'tildi": mavzu guruh uchun ochiladi — test va uy vazifasi o'quvchilarga chiqadi."""

    @extend_schema(request=CoverSerializer, responses={200: TeacherLiveSerializer}, tags=["live"])
    def post(self, request: Request, pk: int) -> Response:
        lesson = self.lesson(request, pk)
        serializer = CoverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        topic: Lesson = get_object_or_404(
            Lesson.objects.select_related("module"), pk=serializer.validated_data["lesson"]
        )
        try:
            services.cover(lesson, topic, request.user)
        except services.LiveError as exc:
            raise live_error(exc) from exc
        return Response(self.payload(request, lesson))

    @extend_schema(request=None, responses={200: TeacherLiveSerializer}, tags=["live"])
    def delete(self, request: Request, pk: int) -> Response:
        lesson = self.lesson(request, pk)
        services.uncover(lesson)
        return Response(self.payload(request, lesson))
