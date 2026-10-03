from typing import Any

from django import forms
from django.contrib import admin, messages
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminSelect2MultipleWidget

from apps.live import services as live
from apps.live.admin import GroupLessonInline, HttpsLinks, ScheduleSlotInline, https_formfield
from apps.live.models import GroupLesson
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import locale_of, text
from apps.users.roles import sees_all

from .models import Enrollment, LessonProgress, StudyGroup


def notify_course_opened(enrollment: Enrollment) -> None:
    """Admin kursni qo'lda ochdi: o'quvchiga kabinet va Telegram orqali xabar."""
    user = enrollment.user
    locale = locale_of(user.locale)
    with translation.override(locale):
        course = str(enrollment.course.title)
    notify(
        user,
        Notification.Kind.COURSE_OPENED,
        title=text(locale, "opened_title"),
        body=text(locale, "opened_body", course=course),
        link=f"/dashboard/courses/{enrollment.course.slug}",
        dedupe_key=f"opened:{enrollment.pk}",
    )


class StudentChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj: Any) -> str:
        user = obj.user
        return f"{user.get_full_name() or user.phone} · {user.phone}"


class StudyGroupForm(forms.ModelForm):
    students = StudentChoiceField(
        label=_("O'quvchilar"),
        queryset=Enrollment.objects.none(),
        required=False,
        widget=UnfoldAdminSelect2MultipleWidget,
        help_text=_(
            "Shu kursga yozilgan va boshqa guruhda bo'lmagan o'quvchilar. "
            "Yangi guruhda avval saqlang, keyin o'quvchilarni tanlang."
        ),
    )

    class Meta:
        model = StudyGroup
        formfield_callback = https_formfield
        fields = [
            "name",
            "course",
            "teacher",
            "study_format",
            "schedule",
            "starts_on",
            "meet_url",
            "room",
            "capacity",
            "status",
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        group = self.instance
        students = self.fields["students"]
        if group.pk and isinstance(students, forms.ModelMultipleChoiceField):
            students.queryset = (
                Enrollment.objects.filter(
                    course_id=group.course_id, status=Enrollment.Status.ACTIVE
                )
                .filter(Q(group__isnull=True) | Q(group=group))
                .select_related("user")
                .order_by("user__first_name", "user__phone")
            )
            students.initial = list(group.enrollments.values_list("pk", flat=True))

    def clean_course(self) -> Any:
        course = self.cleaned_data["course"]
        group = self.instance
        if group.pk and course.pk != group.course_id and group.enrollments.exists():
            raise forms.ValidationError(
                _("Guruhda o'quvchilar bor — kursni o'zgartirib bo'lmaydi.")
            )
        return course


@admin.register(StudyGroup)
class StudyGroupAdmin(HttpsLinks, ModelAdmin):
    """O'qituvchi guruhlari. Menejer guruh ochadi va o'quvchilarni biriktiradi."""

    form = StudyGroupForm
    list_display = (
        "name",
        "course",
        "teacher",
        "study_format",
        "schedule",
        "show_students",
        "show_status",
        "starts_on",
    )
    list_filter = ("status", "study_format", "teacher_paced", "course", "teacher")
    search_fields = ("name", "course__title", "teacher__first_name", "teacher__phone")
    autocomplete_fields = ("course",)
    inlines = [ScheduleSlotInline, GroupLessonInline]
    actions = ["sync_lessons"]
    fieldsets = [
        (None, {"fields": [("name", "course"), ("teacher", "study_format"), "teacher_paced"]}),
        (
            _("Jadval"),
            {
                "fields": [("schedule", "starts_on"), ("meet_url", "room"), ("capacity", "status")],
                "description": _(
                    "Pastdagi haftalik jadvaldan darslar 14 kun oldinga o'zi yaratiladi; "
                    "bitta darsni o'zgartirish yoki bekor qilish — \"Jonli darslar\" bo'limida."
                ),
            },
        ),
        (_("O'quvchilar"), {"fields": ["students"]}),
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[StudyGroup]:
        queryset = (
            super()
            .get_queryset(request)
            .select_related("course", "teacher")
            .annotate(student_total=Count("enrollments"))
        )
        # O'qituvchi — faqat o'z guruhlari.
        return queryset if sees_all(request.user) else queryset.filter(teacher=request.user)

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: bool) -> None:
        super().save_related(request, form, formsets, change)
        if form.instance.pk:
            # Jadval, havola yoki xona o'zgargan bo'lishi mumkin: kelgusi darslar moslanadi.
            created, removed = live.sync(form.instance)
            if created or removed:
                self.message_user(
                    request,
                    _(
                        "Jonli darslar yangilandi: %(created)s ta qo'shildi, "
                        "%(removed)s ta olib tashlandi."
                    )
                    % {"created": created, "removed": removed},
                )
        if "students" not in form.cleaned_data or not form.instance.pk:
            return
        group = form.instance
        selected = {enrollment.pk for enrollment in form.cleaned_data["students"]}
        # Har biri alohida saqlanadi: audit log'da kim, qachon biriktirgani qoladi.
        for enrollment in Enrollment.objects.filter(
            (Q(group=group) & ~Q(pk__in=selected)) | Q(pk__in=selected, group__isnull=True)
        ):
            enrollment.group = group if enrollment.pk in selected else None
            enrollment.save(update_fields=["group", "updated_at"])

    def save_formset(self, request: HttpRequest, form: Any, formset: Any, change: bool) -> None:
        if formset.model is not GroupLesson:
            super().save_formset(request, form, formset, change)
            return
        # Qo'lda belgilangan o'tilgan dars ham o'quvchilarga xabar bilan ochiladi.
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        opened = []
        for obj in instances:
            if obj.pk is None:
                obj.opened_by = request.user
                opened.append(obj)
            obj.save()
        formset.save_m2m()
        for obj in opened:
            live.announce(obj)

    @action(description=_("Jadvaldan darslarni yangilash (14 kun)"))
    def sync_lessons(self, request: HttpRequest, queryset: QuerySet[StudyGroup]) -> None:
        created = sum(live.sync(group)[0] for group in queryset)
        self.message_user(
            request,
            _("%(count)s ta dars yaratildi.") % {"count": created},
            messages.SUCCESS,
        )

    @display(description=_("O'quvchilar"), ordering="student_total")
    def show_students(self, obj: StudyGroup) -> str:
        total = int(getattr(obj, "student_total", 0))
        return f"{total} / {obj.capacity}" if obj.capacity else str(total)

    @display(
        description=_("Holat"),
        ordering="status",
        label={
            StudyGroup.Status.FORMING: "info",
            StudyGroup.Status.ACTIVE: "success",
            StudyGroup.Status.FINISHED: "warning",
        },
    )
    def show_status(self, obj: StudyGroup) -> tuple[str, str]:
        return obj.status, obj.get_status_display()


@admin.register(Enrollment)
class EnrollmentAdmin(ModelAdmin):
    """Kursga kirish huquqi. To'lovsiz (qo'lda) berish ham shu yerdan."""

    list_display = (
        "user",
        "course",
        "show_status",
        "study_format",
        "group",
        "source",
        "expires_at",
    )
    list_filter = ("status", "study_format", "source", "course", "group")
    search_fields = ("user__phone", "user__first_name", "user__last_name", "course__title")
    autocomplete_fields = ("course", "group")
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"
    fieldsets = [
        (None, {"fields": ["user", "course", "group"]}),
        (_("Huquq"), {"fields": [("status", "source"), ("study_format", "expires_at")]}),
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Enrollment]:
        return super().get_queryset(request).select_related("user", "course", "group")

    def save_model(self, request: HttpRequest, obj: Enrollment, form: Any, change: bool) -> None:
        super().save_model(request, obj, form, change)
        opened = not change and obj.status == Enrollment.Status.ACTIVE
        if opened and obj.source == Enrollment.Source.MANUAL:
            notify_course_opened(obj)

    @display(
        description=_("Holat"),
        label={Enrollment.Status.ACTIVE: "success", Enrollment.Status.CANCELLED: "danger"},
    )
    def show_status(self, obj: Enrollment) -> tuple[str, str]:
        if obj.status == Enrollment.Status.ACTIVE and not obj.is_open:
            return Enrollment.Status.CANCELLED, str(_("Muddati o'tgan"))
        return obj.status, obj.get_status_display()


@admin.register(LessonProgress)
class LessonProgressAdmin(ModelAdmin):
    """Faqat ko'rish uchun: progress pleyerdan yoziladi."""

    list_display = ("user", "lesson", "show_position", "show_done", "updated_at")
    list_filter = ("lesson__module__course",)
    search_fields = ("user__phone", "lesson__title")
    date_hierarchy = "updated_at"
    readonly_fields = ("user", "lesson", "position_sec", "watched_sec", "completed_at")

    def get_queryset(self, request: HttpRequest) -> QuerySet[LessonProgress]:
        return (
            super()
            .get_queryset(request)
            .select_related("user", "lesson", "lesson__module", "lesson__module__course")
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @display(description=_("To'xtagan joyi"), ordering="position_sec")
    def show_position(self, obj: LessonProgress) -> str:
        minutes, seconds = divmod(obj.position_sec, 60)
        return f"{minutes}:{seconds:02d}"

    @display(description=_("Tugatildi"), boolean=True, ordering="completed_at")
    def show_done(self, obj: LessonProgress) -> bool:
        return obj.completed
