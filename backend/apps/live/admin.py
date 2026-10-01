"""Admin: guruhning haftalik jadvali (guruh sahifasida), jonli darslar va davomat.

O'qituvchi faqat o'z guruhlarini ko'radi; jadvalni menejer va admin qo'yadi.
"""

from typing import Any

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q, QuerySet
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from apps.learning.models import StudyGroup
from apps.users.roles import sees_all

from . import services
from .models import Attendance, GroupLesson, LiveLesson, ScheduleSlot


def scope_groups[M: Any](queryset: QuerySet[M], user: Any, path: str) -> QuerySet[M]:
    """O'qituvchi — faqat o'z guruhlari (`path` — modeldan guruhgacha yo'l)."""
    if sees_all(user):
        return queryset
    return queryset.filter(**{f"{path}teacher": user})


def https_formfield(db_field: Any, **kwargs: Any) -> Any:
    """ModelForm uchun (`Meta.formfield_callback`): sxemasiz havolaga https:// qo'shiladi."""
    if isinstance(db_field, models.URLField):
        kwargs.setdefault("assume_scheme", "https")
    return db_field.formfield(**kwargs)


class HttpsLinks:
    """Havola sxemasiz yozilsa (meet.google.com/...) — https:// qo'shiladi (Django 6.0 kabi)."""

    def formfield_for_dbfield(self, db_field: Any, request: HttpRequest, **kwargs: Any) -> Any:
        if isinstance(db_field, models.URLField):
            kwargs.setdefault("assume_scheme", "https")
        return super().formfield_for_dbfield(db_field, request, **kwargs)  # type: ignore[misc]


class ScheduleSlotInline(TabularInline):
    """Guruh sahifasida: haftalik jadval. Darslar 14 kun oldinga shundan yaratiladi."""

    model = ScheduleSlot
    extra = 0
    fields = ("weekday", "starts_at", "duration_min")
    verbose_name = _("jadvaldagi dars")
    verbose_name_plural = _("haftalik jadval")


class GroupLessonFormSet(BaseInlineFormSet):
    def clean(self) -> None:
        super().clean()
        group = self.instance
        for form in self.forms:
            data = form.cleaned_data or {}
            lesson = data.get("lesson")
            if lesson is None or data.get("DELETE"):
                continue
            if lesson.module.course_id != group.course_id:
                raise ValidationError(
                    _("«%(lesson)s» guruh kursiga tegishli emas.") % {"lesson": lesson}
                )


class GroupLessonInline(TabularInline):
    """Offlayn guruh: o'tilgan darslar — shu darsgacha test va uy vazifalari o'quvchilarga ochiq.
    Odatda ustoz jadvaldagi darsda "Dars o'tildi" deydi; bu yerda qo'lda ham belgilanadi."""

    model = GroupLesson
    formset = GroupLessonFormSet
    extra = 0
    fields = ("lesson", "opened_at", "opened_by")
    readonly_fields = ("opened_at", "opened_by")
    autocomplete_fields = ("lesson",)
    verbose_name = _("o'tilgan dars")
    verbose_name_plural = _("o'tilgan darslar (shu darsgacha test va vazifalar ochiq)")


class AttendanceInline(TabularInline):
    model = Attendance
    extra = 0
    fields = ("student", "status", "joined_at", "marked_by", "marked_at")
    readonly_fields = ("student", "joined_at", "marked_by", "marked_at")
    can_delete = False

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        # Ro'yxat o'quvchilar bilan birga keladi: davomat asosan o'qituvchi sahifasida belgilanadi.
        return False


@admin.register(LiveLesson)
class LiveLessonAdmin(HttpsLinks, ModelAdmin):
    list_display = ("starts_at", "group", "kind", "show_state", "show_attendance")
    list_filter = ("kind", "group__course", "group")
    list_select_related = ("group", "group__course")
    search_fields = ("group__name", "title", "topic__title")
    date_hierarchy = "starts_at"
    autocomplete_fields = ("topic",)
    inlines = [AttendanceInline]
    readonly_fields = ("canceled_at",)
    actions = ["cancel_selected"]
    fieldsets = (
        (None, {"fields": (("group", "starts_at"), ("duration_min", "kind"))}),
        (_("Qayerda"), {"fields": (("meet_url", "room"),)}),
        (_("Mazmun"), {"fields": (("topic", "title"), "notes", "recording_url")}),
        (_("Bekor qilish"), {"fields": (("canceled_at", "cancel_reason"),)}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[LiveLesson]:
        queryset = (
            super()
            .get_queryset(request)
            .annotate(
                marked=Count("attendance", filter=~Q(attendance__status="")),
                came=Count(
                    "attendance",
                    filter=Q(
                        attendance__status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE]
                    ),
                ),
            )
        )
        return scope_groups(queryset, request.user, "group__")

    def formfield_for_foreignkey(self, db_field: Any, request: HttpRequest, **kwargs: Any) -> Any:
        if db_field.name == "group":
            kwargs["queryset"] = scope_groups(StudyGroup.objects.all(), request.user, "")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request: HttpRequest, obj: LiveLesson, form: Any, change: bool) -> None:
        # Qo'lda o'zgartirilgan dars jadval o'zgarganda qayta yaratilmaydi.
        obj.generated = False
        recording = "recording_url" in form.changed_data and obj.recording_url
        super().save_model(request, obj, form, change)
        if change and recording:
            services.set_recording(obj, obj.recording_url)

    @display(description=_("Holat"))
    def show_state(self, obj: LiveLesson) -> str:
        if obj.is_canceled:
            return str(_("Bekor qilindi"))
        now = timezone.now()
        if obj.ends_at <= now:
            return str(_("O'tdi"))
        if obj.starts_at <= now:
            return str(_("Ketmoqda"))
        return str(_("Rejada"))

    @display(description=_("Davomat"))
    def show_attendance(self, obj: LiveLesson) -> str:
        marked = obj.marked  # type: ignore[attr-defined]
        return "—" if not marked else f"{obj.came}/{marked}"  # type: ignore[attr-defined]

    @action(description=_("Tanlangan darslarni bekor qilish"))
    def cancel_selected(self, request: HttpRequest, queryset: QuerySet[LiveLesson]) -> None:
        done = 0
        for lesson in queryset.select_related("group__course", "group__teacher"):
            try:
                services.cancel(lesson, "", by=request.user)
            except services.LiveError:
                continue
            done += 1
        self.message_user(
            request,
            ngettext("%(count)s ta dars bekor qilindi.", "%(count)s ta dars bekor qilindi.", done)
            % {"count": done},
            messages.SUCCESS if done else messages.WARNING,
        )


@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin):
    """Davomat: ko'rish va holatni tuzatish."""

    list_display = ("student", "live_lesson", "status", "joined_at", "marked_by")
    list_filter = ("status", "live_lesson__group")
    list_select_related = ("student", "live_lesson__group", "marked_by")
    search_fields = ("student__phone", "student__first_name", "student__last_name")
    fields = ("student", "live_lesson", "status", "joined_at", "marked_by", "marked_at")
    readonly_fields = ("student", "live_lesson", "joined_at", "marked_by", "marked_at")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Attendance]:
        return scope_groups(super().get_queryset(request), request.user, "live_lesson__group__")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def save_model(self, request: HttpRequest, obj: Attendance, form: Any, change: bool) -> None:
        obj.marked_by = request.user  # type: ignore[assignment]
        obj.marked_at = timezone.now()
        super().save_model(request, obj, form, change)
