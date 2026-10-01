from typing import Any

from django.contrib import admin
from django.db import models
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from unfold.admin import StackedInline, TabularInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import display

from apps.core.admin_utils import FORMFIELD_OVERRIDES, TranslatedModelAdmin, language_tabs
from apps.homework.admin import AssignmentInline
from apps.quizzes.admin import QuizInline
from apps.videos.widgets import VideoUploadWidget

from .models import Category, Course, Instructor, Lesson, LessonMaterial, Module
from .scope import TeacherScopedAdmin, scope_videos


def money(amount: int) -> str:
    """1 800 000 so'm ko'rinishida."""
    return f"{amount:,} so'm".replace(",", " ")


@admin.register(Category)
class CategoryAdmin(TranslatedModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name_uz",)}
    ordering_field = "order"
    hide_ordering_field = True
    fieldsets = [(None, {"fields": ["slug"]}), *language_tabs(["name"])]


@admin.register(Instructor)
class InstructorAdmin(TranslatedModelAdmin):
    list_display = ("full_name", "position", "experience_years", "is_published")
    list_filter = ("is_published",)
    search_fields = ("full_name", "slug")
    prepopulated_fields = {"slug": ("full_name",)}
    ordering_field = "order"
    hide_ordering_field = True
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "full_name",
                    "slug",
                    "photo",
                    "experience_years",
                    "is_published",
                    "user",
                ]
            },
        ),
        (_("Ijtimoiy tarmoqlar"), {"fields": ["telegram_url", "linkedin_url", "github_url"]}),
        *language_tabs(["position", "bio"]),
    ]
    raw_id_fields = ("user",)

    def formfield_for_dbfield(self, db_field: Any, request: HttpRequest, **kwargs: Any) -> Any:
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "user" and field is not None:
            field.help_text = _(
                "O'qituvchining akkaunti. Bog'lansa, u admin panelda shu ustoz biriktirilgan "
                "kurslarning darslari va materiallarini ko'radi (rol: O'qituvchi)."
            )
        return field


class ModuleInline(TabularInline):
    """Kurs sahifasidagi dastur: modullar ro'yxati. Darslar modul sahifasida."""

    model = Module
    extra = 0
    fields = ("title_uz", "summary_uz", "order")
    ordering = ("order", "id")
    show_change_link = True


class LessonInline(TabularInline):
    """Modul sahifasidagi darslar."""

    model = Lesson
    extra = 0
    fields = ("title_uz", "video_status", "duration_min", "is_preview", "order")
    readonly_fields = ("video_status",)
    ordering = ("order", "id")
    show_change_link = True

    @display(description=_("Video"))
    def video_status(self, obj: Lesson) -> str:
        video = obj.video
        return str(video.get_status_display()) if video else "—"


@admin.register(Course)
class CourseAdmin(TeacherScopedAdmin, TranslatedModelAdmin):
    teacher_course_path = "pk"

    list_display = (
        "title",
        "category",
        "show_audience",
        "show_status",
        "show_price",
        "show_program",
    )
    list_filter = ("status", "audience", "study_format", "is_free", "category", "level")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title_uz",)}
    autocomplete_fields = ("instructors",)
    ordering_field = "order"
    hide_ordering_field = True
    formfield_overrides = {models.TextField: {"widget": WysiwygWidget}}
    inlines = [ModuleInline]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "slug",
                    "category",
                    "instructors",
                    ("audience", "level", "status"),
                    ("age_min", "age_max"),
                    ("video_language", "icon"),
                    "cover",
                    ("mxik_code", "is_featured"),
                ]
            },
        ),
        (
            _("Narx va shakl"),
            {
                "fields": [
                    "study_format",
                    "is_free",
                    ("price_online", "price_offline_monthly"),
                    "duration_hours",
                    ("monthly_exam", "certificate"),
                ],
                "description": _(
                    "Onlayn — bir martalik to'lov, offlayn — oyma-oy to'lov. «Bepul» "
                    "belgilansa, kursni ro'yxatdan o'tgan har kim o'qiy oladi."
                ),
            },
        ),
        *language_tabs(["title", "short_description", "description"]),
    ]

    @display(
        description=_("Holat"),
        label={
            Course.Status.DRAFT: "warning",
            Course.Status.PUBLISHED: "success",
            Course.Status.ARCHIVED: "info",
        },
    )
    def show_status(self, obj: Course) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description=_("Kimga"), ordering="audience")
    def show_audience(self, obj: Course) -> str:
        if obj.age_min and obj.age_max:
            return f"{obj.age_min}–{obj.age_max} yosh"
        return str(obj.get_audience_display())

    @display(description=_("Narx"), ordering="price_online")
    def show_price(self, obj: Course) -> str:
        if obj.is_free:
            return str(_("Bepul"))
        parts = []
        if obj.study_format in (Course.Format.ONLINE, Course.Format.BOTH):
            parts.append(f"{money(obj.price_online)} (bir marta)")
        if obj.study_format in (Course.Format.OFFLINE, Course.Format.BOTH):
            parts.append(f"{money(obj.price_offline_monthly)}/oy")
        return " · ".join(parts) or "—"

    @display(description=_("Dastur"), ordering="lesson_count")
    def show_program(self, obj: Course) -> str:
        if not obj.lesson_count:
            return "—"
        hours, minutes = divmod(obj.total_duration_min, 60)
        length = f"{hours} s {minutes} daq" if hours else f"{minutes} daq"
        return f"{obj.lesson_count} dars · {length}"


@admin.register(Module)
class ModuleAdmin(TeacherScopedAdmin, TranslatedModelAdmin):
    teacher_course_path = "course"
    teacher_scoped_fields = {"course": "pk"}

    list_display = ("title", "course", "show_lessons", "order")
    list_filter = ("course",)
    search_fields = ("title", "course__title")
    autocomplete_fields = ("course",)
    ordering_field = "order"
    hide_ordering_field = True
    inlines = [LessonInline]
    fieldsets = [(None, {"fields": ["course"]}), *language_tabs(["title", "summary"])]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Module]:
        return (
            super()
            .get_queryset(request)
            .select_related("course")
            .annotate(lesson_total=Count("lessons"))
        )

    @display(description=_("Darslar"), ordering="lesson_total")
    def show_lessons(self, obj: Module) -> int:
        # `lesson_total` get_queryset'dagi annotate'dan keladi.
        return int(getattr(obj, "lesson_total", 0))


class MaterialInline(StackedInline):
    """Dars materiallari: fayl, havola yoki darsda yozilgan kod."""

    model = LessonMaterial
    extra = 0
    ordering = ("order", "id")
    formfield_overrides = FORMFIELD_OVERRIDES
    fields = (("kind", "title", "order"), "file", "url", ("language",), "code")


@admin.register(Lesson)
class LessonAdmin(TeacherScopedAdmin, TranslatedModelAdmin):
    teacher_course_path = "module__course"
    teacher_scoped_fields = {"module": "course"}

    list_display = ("title", "module", "show_video", "duration_min", "is_preview")
    list_filter = ("is_preview", "module__course", "video__status")
    search_fields = ("title", "module__title")
    autocomplete_fields = ("module",)
    ordering_field = "order"
    hide_ordering_field = True
    inlines = [MaterialInline, AssignmentInline, QuizInline]
    fieldsets = [
        (None, {"fields": ["module", ("duration_min", "is_preview")]}),
        (
            _("Video"),
            {
                "fields": ["video"],
                "description": _(
                    "Fayl brauzerdan to'g'ridan-to'g'ri saqlovga yuklanadi. Yuklash tugagach "
                    "video avtomatik qayta ishlanadi va dars davomiyligi yangilanadi."
                ),
            },
        ),
        *language_tabs(["title", "summary"]),
    ]

    def formfield_for_foreignkey(self, db_field: Any, request: HttpRequest, **kwargs: Any) -> Any:
        if db_field.name == "video":
            kwargs["widget"] = VideoUploadWidget()
            kwargs["queryset"] = scope_videos(
                db_field.remote_field.model._default_manager.all(), request.user
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Lesson]:
        return super().get_queryset(request).select_related("module", "video")

    @display(description=_("Video"), ordering="video__status")
    def show_video(self, obj: Lesson) -> str:
        video = obj.video
        return str(video.get_status_display()) if video else "—"
