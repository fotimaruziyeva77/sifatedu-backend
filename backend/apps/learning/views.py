"""Kabinet: mening kurslarim, dars sahifasi, himoyalangan video va progress."""

from typing import Any

from django.conf import settings
from django.db.models import Prefetch, QuerySet
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Course, Lesson, LessonMaterial, Module
from apps.core import events
from apps.homework.services import homework_payload
from apps.live.gates import tasks_open
from apps.quizzes.services import course_stars, quiz_summary
from apps.videos import hls, s3
from apps.videos.models import VideoAsset

from . import access
from .models import COMPLETE_RATIO, Enrollment, LessonProgress
from .serializers import (
    EnrollSerializer,
    LessonPlayerSerializer,
    LessonProgressSerializer,
    MyCourseDetailSerializer,
    MyCourseSerializer,
    ProgressUpdateSerializer,
)


def lesson_queryset() -> QuerySet[Lesson]:
    return Lesson.objects.select_related("module", "module__course", "video").prefetch_related(
        "materials"
    )


def completed_ids(user: Any, course: Course) -> set[int]:
    person = access.student(user)
    if person is None:
        return set()
    return set(
        LessonProgress.objects.filter(
            user=person, lesson__module__course=course, completed_at__isnull=False
        ).values_list("lesson_id", flat=True)
    )


def watermark_for(user: Any) -> str:
    """Video ustida ko'rinadi: raqamning oxirgi to'rt raqami va akkaunt raqami."""
    if not getattr(user, "is_authenticated", False):
        return ""
    phone = getattr(user, "phone", "") or ""
    return f"{phone[-4:]} · #{user.pk}"


def materials_payload(lesson: Lesson) -> list[dict[str, Any]]:
    """Dars materiallari. Chaqiruvchi darsga kirish huquqini oldin tekshirgan bo'ladi."""
    ttl = settings.HLS_SIGNED_URL_TTL_SEC
    items = []
    for material in lesson.materials.all():
        url = material.url
        size = None
        if material.kind == LessonMaterial.Kind.FILE and material.file:
            name = material.file.name.rsplit("/", 1)[-1]
            url = s3.sign_get(material.file.name, ttl, download_name=name)
            try:
                size = material.file.size
            except Exception:
                # Storage javob bermasa ham dars sahifasi ochiladi, faqat hajmi ko'rinmaydi.
                size = None
        items.append(
            {
                "id": material.pk,
                "kind": material.kind,
                "title": material.title,
                "url": url,
                "code": material.code if material.kind == LessonMaterial.Kind.CODE else "",
                "language": material.language,
                "size": size,
            }
        )
    return items


def course_card(
    course: Course,
    done: set[int],
    enrollment: Enrollment | None,
    gate: dict[int, int] | None = None,
) -> dict[str, Any]:
    lessons = [lesson for module in course.modules.all() for lesson in module.lessons.all()]
    total = len(lessons)
    finished = sum(1 for lesson in lessons if lesson.pk in done)
    upcoming = next((lesson for lesson in lessons if lesson.pk not in done), None)
    # Keyingi dars testdan o'tilmagani uchun yopiq bo'lsa — o'sha testli darsga olib boramiz.
    upcoming_id = (gate or {}).get(upcoming.pk, upcoming.pk) if upcoming else None
    return {
        "slug": course.slug,
        "title": course.title,
        "icon": course.icon,
        "cover": course.cover.url if course.cover else "",
        "audience": course.audience,
        # O'quvchi uchun muhim — o'zi tanlagan shakl (kurs "BOTH" bo'lsa ham).
        "study_format": enrollment.study_format if enrollment else course.study_format,
        "is_free": course.is_free,
        # To'lab olingan kurs: kabinetda "premium" ko'rinish.
        "is_premium": bool(enrollment and enrollment.source == Enrollment.Source.PAYMENT),
        "total_duration_min": sum(lesson.duration_min for lesson in lessons),
        "lesson_count": total,
        "completed_count": finished,
        "percent": round(finished * 100 / total) if total else 0,
        "expires_at": enrollment.expires_at if enrollment else None,
        # Tugatilmagan birinchi dars: "davom ettirish" tugmasi shu yerga olib boradi.
        "next_lesson_id": upcoming_id or (lessons[0].pk if lessons else None),
    }


def with_program(queryset: QuerySet[Course]) -> QuerySet[Course]:
    lessons = Lesson.objects.order_by("order", "id").select_related("video")
    return queryset.prefetch_related(
        Prefetch(
            "modules",
            queryset=Module.objects.order_by("order", "id").prefetch_related(
                Prefetch("lessons", queryset=lessons)
            ),
        )
    )


@extend_schema(tags=["learning"], responses=MyCourseSerializer(many=True))
class MyCoursesView(APIView):
    """Kabinet bosh sahifasi va "mening kurslarim"."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        courses = with_program(access.enrolled_courses(request.user)).order_by("order", "id")
        enrollments = {
            enrollment.course_id: enrollment
            for enrollment in Enrollment.objects.filter(user=request.user.pk)
        }
        cards = []
        for course in courses:
            done = completed_ids(request.user, course)
            gate = access.quiz_gate(request.user, course.pk)
            cards.append(course_card(course, done, enrollments.get(course.pk), gate))
        return Response(cards)


@extend_schema(tags=["learning"], responses=MyCourseDetailSerializer)
class MyCourseView(APIView):
    """Kurs dasturi: sidebar uchun modullar, darslar va qulflar."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, slug: str) -> Response:
        course = get_object_or_404(with_program(Course.objects.all()), slug=slug)
        if not access.can_open_course(request.user, course):
            raise PermissionDenied("Bu kursga kirish huquqingiz yo'q.")
        access.ensure_free_enrollment(request.user, course)

        done = completed_ids(request.user, course)
        enrollment = access.open_enrollment(request.user, course)
        stars = course_stars(request.user, course)
        # Kursga huquq yuqorida tekshirildi: dars faqat test sababli yopiq bo'lishi mumkin.
        gate = access.quiz_gate(request.user, course.pk)
        payload = course_card(course, done, enrollment, gate)
        payload["modules"] = [
            {
                "id": module.pk,
                "title": module.title,
                "lessons": [
                    {
                        "id": lesson.pk,
                        "title": lesson.title,
                        "duration_min": lesson.duration_min,
                        "is_preview": lesson.is_preview,
                        "has_video": lesson.video_id is not None,
                        "locked": lesson.pk in gate,
                        "lock_reason": access.LOCK_QUIZ if lesson.pk in gate else None,
                        "blocked_by": gate.get(lesson.pk),
                        "completed": lesson.pk in done,
                        "quiz_stars": stars.get(lesson.pk),
                    }
                    for lesson in module.lessons.all()
                ],
            }
            for module in course.modules.all()
        ]
        return Response(payload)


class LessonAccessView(APIView):
    """Darsga kirish huquqi bitta joyda tekshiriladi (apps/learning/access.py)."""

    # Bepul (preview) darsni kirmagan foydalanuvchi ham ko'radi.
    permission_classes = [AllowAny]

    def lesson(self, request: Request, pk: int) -> Lesson:
        lesson = get_object_or_404(lesson_queryset(), pk=pk)
        if not access.can_open_lesson(request.user, lesson):
            raise PermissionDenied("Bu dars sizga ochiq emas.")
        return lesson

    def ready_video(self, lesson: Lesson) -> VideoAsset:
        video = lesson.video
        if video is None or not video.is_ready:
            raise NotFound("Bu darsning videosi hali tayyor emas.")
        return video


@extend_schema(tags=["learning"], responses=LessonPlayerSerializer)
class LessonPlayerView(LessonAccessView):
    def get(self, request: Request, pk: int) -> Response:
        lesson = self.lesson(request, pk)
        siblings = list(
            Lesson.objects.filter(module__course=lesson.module.course)
            .order_by("module__order", "module__id", "order", "id")
            .values_list("id", flat=True)
        )
        index = siblings.index(lesson.pk)
        progress = self.progress(request, lesson)
        # Offlayn guruhda test va vazifa ustoz "Dars o'tildi" deb belgilagach ko'rinadi.
        locked = not tasks_open(request.user, lesson)
        return Response(
            {
                "id": lesson.pk,
                "title": lesson.title,
                "summary": lesson.summary,
                "duration_min": lesson.duration_min,
                "is_preview": lesson.is_preview,
                "module_title": lesson.module.title,
                "course_slug": lesson.module.course.slug,
                "course_title": lesson.module.course.title,
                "prev_id": siblings[index - 1] if index > 0 else None,
                "next_id": siblings[index + 1] if index + 1 < len(siblings) else None,
                "video": self.video_payload(lesson),
                "progress": {
                    "position_sec": progress[0],
                    "watched_sec": progress[1],
                    "completed": progress[2],
                },
                "materials": materials_payload(lesson),
                "watermark": watermark_for(request.user),
                "homework": None if locked else homework_payload(lesson, request.user),
                "quiz": None if locked else quiz_summary(lesson, request.user),
                "tasks_locked": locked,
            }
        )

    def progress(self, request: Request, lesson: Lesson) -> tuple[int, int, bool]:
        if not request.user.is_authenticated:
            return 0, 0, False
        row = LessonProgress.objects.filter(user__pk=request.user.pk, lesson=lesson).first()
        if row is None:
            return 0, 0, False
        return row.position_sec, row.watched_sec, row.completed

    def video_payload(self, lesson: Lesson) -> dict[str, Any] | None:
        video = lesson.video
        if video is None:
            return None
        return {
            "status": video.status,
            "duration_sec": video.duration_sec,
            "poster": video.thumbnail.url if video.thumbnail else "",
            "hls_url": (
                reverse("lesson-hls-master", kwargs={"pk": lesson.pk}) if video.is_ready else ""
            ),
        }


@extend_schema(tags=["learning"], responses={200: {"type": "string"}})
class LessonMasterPlaylistView(LessonAccessView):
    """Sifatlar ro'yxati. Har bir sifat alohida so'rov bilan olinadi."""

    def get(self, request: Request, pk: int) -> HttpResponse:
        lesson = self.lesson(request, pk)
        video = self.ready_video(lesson)
        template = reverse("lesson-hls-rendition", kwargs={"pk": lesson.pk, "name": "NAME"})
        body = hls.master(video, template.replace("NAME", "{name}"))
        return HttpResponse(body, content_type=hls.PLAYLIST_CONTENT_TYPE)


@extend_schema(tags=["learning"], responses={200: {"type": "string"}})
class LessonRenditionPlaylistView(LessonAccessView):
    """Segment havolalari imzolangan va qisqa muddatli."""

    def get(self, request: Request, pk: int, name: str) -> HttpResponse:
        lesson = self.lesson(request, pk)
        video = self.ready_video(lesson)
        key_url = reverse("lesson-hls-key", kwargs={"pk": lesson.pk})
        body = hls.rendition(video, name, key_url)
        if body is None:
            raise NotFound("Bunday sifat yo'q.")
        return HttpResponse(body, content_type=hls.PLAYLIST_CONTENT_TYPE)


@extend_schema(tags=["learning"], responses={200: {"type": "string", "format": "binary"}})
class LessonKeyView(LessonAccessView):
    """AES-128 kaliti. Faqat shu darsga huquqi bori oladi."""

    def get(self, request: Request, pk: int) -> HttpResponse:
        lesson = self.lesson(request, pk)
        video = self.ready_video(lesson)
        response = HttpResponse(video.ensure_key(), content_type="application/octet-stream")
        # Kalit keshda qolmasligi kerak: huquq bekor qilinsa, keyingi so'rov to'xtaydi.
        response["Cache-Control"] = "no-store"
        return response


@extend_schema(
    tags=["learning"], request=ProgressUpdateSerializer, responses=LessonProgressSerializer
)
class LessonProgressView(APIView):
    """Pleyer har 15 soniyada va pauzada shu yerga yozadi."""

    permission_classes = [IsAuthenticated]

    def put(self, request: Request, pk: int) -> Response:
        lesson = get_object_or_404(lesson_queryset(), pk=pk)
        if not access.can_open_lesson(request.user, lesson):
            raise PermissionDenied("Bu dars sizga ochiq emas.")
        form = ProgressUpdateSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        total = lesson.video.duration_sec if lesson.video else lesson.duration_min * 60
        # Davomiylik ma'lum bo'lsa, pozitsiya undan oshmaydi.
        position = min(form.validated_data["position_sec"], total) if total else 0
        row, _created = LessonProgress.objects.get_or_create(user_id=request.user.pk, lesson=lesson)
        row.position_sec = position
        # Ko'rilgan vaqt faqat oshadi: orqaga qaytarsa ham kamaymaydi.
        row.watched_sec = max(row.watched_sec, form.validated_data.get("watched_sec", position))
        completed = row.completed_at is None and total and position >= total * COMPLETE_RATIO
        if completed:
            row.completed_at = timezone.now()
        row.save(update_fields=["position_sec", "watched_sec", "completed_at", "updated_at"])
        if completed:
            events.lesson_completed.send(
                sender=LessonProgress,
                user_id=request.user.pk,
                course_id=lesson.module.course_id,
                lesson_id=lesson.pk,
            )
        return Response(
            {
                "position_sec": row.position_sec,
                "watched_sec": row.watched_sec,
                "completed": row.completed,
            }
        )


@extend_schema(tags=["learning"], request=EnrollSerializer, responses=MyCourseSerializer)
class EnrollFreeView(APIView):
    """Bepul kursni boshlash: to'lov shart emas, faqat ro'yxatdan o'tgan bo'lish kerak."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, slug: str) -> Response:
        course = get_object_or_404(
            with_program(Course.objects.filter(status=Course.Status.PUBLISHED)), slug=slug
        )
        if not course.is_free:
            raise ValidationError({"detail": "Bu kurs pullik. To'lovdan keyin ochiladi."})
        enrollment = access.ensure_free_enrollment(request.user, course)
        done = completed_ids(request.user, course)
        return Response(course_card(course, done, enrollment), status=status.HTTP_201_CREATED)
