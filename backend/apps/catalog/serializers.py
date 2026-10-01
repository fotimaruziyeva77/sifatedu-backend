from rest_framework import serializers

from apps.core.serializers import ReadOnlyModelSerializer

from .models import Category, Course, Instructor, Lesson, Module


class CategorySerializer(ReadOnlyModelSerializer):
    """Katalog filtri uchun: kategoriya va undagi nashr qilingan kurslar soni."""

    course_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("slug", "name", "course_count")


class CategoryShortSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Category
        fields = ("slug", "name")


class InstructorShortSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Instructor
        fields = ("slug", "full_name")


class InstructorCardSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Instructor
        fields = (
            "slug",
            "full_name",
            "position",
            "bio",
            "photo",
            "experience_years",
            "telegram_url",
            "linkedin_url",
            "github_url",
        )


class CourseCardSerializer(ReadOnlyModelSerializer):
    """Kurs kartochkasi: landing va katalogda bir xil ko'rinadi."""

    category = CategoryShortSerializer()
    instructors = InstructorShortSerializer(many=True)

    class Meta:
        model = Course
        fields = (
            "slug",
            "title",
            "short_description",
            "level",
            "audience",
            "study_format",
            "is_free",
            "price_online",
            "price_offline_monthly",
            "age_min",
            "age_max",
            "duration_hours",
            "video_language",
            "icon",
            "cover",
            "category",
            "instructors",
            "lesson_count",
            "total_duration_min",
        )


class LessonSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Lesson
        fields = ("id", "title", "summary", "duration_min", "is_preview")


class ModuleSerializer(ReadOnlyModelSerializer):
    lessons = LessonSerializer(many=True)

    class Meta:
        model = Module
        fields = ("id", "title", "summary", "lessons")


class CourseDetailSerializer(ReadOnlyModelSerializer):
    """Kurs sahifasi: tavsif, dastur va ustozlar."""

    category = CategoryShortSerializer()
    instructors = InstructorCardSerializer(many=True)
    modules = ModuleSerializer(many=True)

    class Meta:
        model = Course
        fields = (
            "slug",
            "title",
            "short_description",
            "description",
            "level",
            "audience",
            "study_format",
            "is_free",
            "price_online",
            "price_offline_monthly",
            "age_min",
            "age_max",
            "duration_hours",
            "video_language",
            "icon",
            "cover",
            "category",
            "instructors",
            "modules",
            "lesson_count",
            "total_duration_min",
        )
