from typing import Any

from rest_framework import serializers

from apps.core.serializers import ReadOnlyModelSerializer
from apps.homework.serializers import HomeworkSerializer
from apps.quizzes.serializers import QuizSummarySerializer

from .models import LessonProgress


class MyLessonSerializer(serializers.Serializer[dict[str, Any]]):
    """Kabinetdagi darslar ro'yxati (sidebar uchun)."""

    id = serializers.IntegerField()
    title = serializers.CharField()
    duration_min = serializers.IntegerField()
    is_preview = serializers.BooleanField()
    has_video = serializers.BooleanField()
    locked = serializers.BooleanField()
    lock_reason = serializers.ChoiceField(
        choices=["access", "quiz"],
        allow_null=True,
        help_text="quiz — oldingi darsning testidan o'tilmagan (onlayn o'quvchi).",
    )
    blocked_by = serializers.IntegerField(
        allow_null=True, help_text="Testi o'tilishi kerak bo'lgan dars (lock_reason=quiz)."
    )
    completed = serializers.BooleanField()
    quiz_stars = serializers.IntegerField(
        allow_null=True, help_text="Testli dars: eng yaxshi yulduz (0–3); test yo'q — null."
    )


class MyModuleSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    title = serializers.CharField()
    lessons = MyLessonSerializer(many=True)


class MyCourseSerializer(serializers.Serializer[dict[str, Any]]):
    """Kurs kartochkasi kabinetda: progress va "davom ettirish"."""

    slug = serializers.CharField()
    title = serializers.CharField()
    icon = serializers.CharField()
    cover = serializers.CharField(allow_blank=True)
    audience = serializers.CharField()
    study_format = serializers.CharField(
        help_text="O'quvchi yozilgan shakl (ONLINE/OFFLINE); yozilmagan xodimga — kursniki."
    )
    is_free = serializers.BooleanField()
    is_premium = serializers.BooleanField()
    total_duration_min = serializers.IntegerField()
    lesson_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    percent = serializers.IntegerField()
    expires_at = serializers.DateTimeField(allow_null=True)
    next_lesson_id = serializers.IntegerField(allow_null=True)


class MyCourseDetailSerializer(MyCourseSerializer):
    modules = MyModuleSerializer(many=True)


class LessonVideoSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField()
    duration_sec = serializers.IntegerField()
    poster = serializers.CharField(allow_blank=True)
    hls_url = serializers.CharField(allow_blank=True)


class LessonProgressSerializer(ReadOnlyModelSerializer):
    completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = LessonProgress
        fields = ("position_sec", "watched_sec", "completed")


class LessonMaterialSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=["FILE", "LINK", "CODE"])
    title = serializers.CharField()
    # Fayl uchun — qisqa muddatli yuklab olish havolasi, havola uchun — manzilning o'zi.
    url = serializers.CharField(allow_blank=True)
    code = serializers.CharField(allow_blank=True)
    language = serializers.CharField(allow_blank=True)
    size = serializers.IntegerField(allow_null=True)


class LessonPlayerSerializer(serializers.Serializer[dict[str, Any]]):
    """Dars sahifasi uchun hamma narsa bitta so'rovda."""

    id = serializers.IntegerField()
    title = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    duration_min = serializers.IntegerField()
    is_preview = serializers.BooleanField()
    module_title = serializers.CharField()
    course_slug = serializers.CharField()
    course_title = serializers.CharField()
    prev_id = serializers.IntegerField(allow_null=True)
    next_id = serializers.IntegerField(allow_null=True)
    video = LessonVideoSerializer(allow_null=True)
    progress = LessonProgressSerializer()
    materials = LessonMaterialSerializer(many=True)
    # Ekrandan yozib olishni to'xtatmaydi, lekin kim yozganini ko'rsatadi.
    watermark = serializers.CharField(allow_blank=True)
    homework = HomeworkSerializer(allow_null=True, help_text="Darsning uy vazifasi (bo'lsa).")
    quiz = QuizSummarySerializer(allow_null=True, help_text="Darsning testi (bo'lsa).")
    tasks_locked = serializers.BooleanField(
        help_text="Offlayn guruh: test va uy vazifasi ustoz darsni o'tgach ochiladi."
    )


class ProgressUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    position_sec = serializers.IntegerField(min_value=0, max_value=60 * 60 * 24)
    watched_sec = serializers.IntegerField(min_value=0, max_value=60 * 60 * 24, required=False)


class EnrollSerializer(serializers.Serializer[dict[str, Any]]):
    slug = serializers.CharField(max_length=60)
