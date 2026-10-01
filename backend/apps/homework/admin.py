"""Admin: darsga uy vazifasi (dars sahifasida) va javoblar ro'yxati (faqat ko'rish).

Javoblarni o'qituvchi kabinetda tekshiradi (kod, rasmlar, tarix bir sahifada); bu yerda —
kuzatish uchun ro'yxat va havola.
"""

from typing import Any

from django.conf import settings
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, StackedInline
from unfold.decorators import display

from apps.users.roles import sees_all

from . import services
from .models import Assignment, Submission


class AssignmentInline(StackedInline):
    model = Assignment
    extra = 0
    max_num = 1
    fields = ("title", "instructions", "deadline")
    verbose_name = _("uy vazifasi")
    verbose_name_plural = _("uy vazifasi")


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = (
        "student",
        "assignment",
        "attempt",
        "show_status",
        "score",
        "late",
        "created_at",
        "reviewer",
    )
    list_filter = ("status", "late", "assignment__lesson__module__course")
    search_fields = ("student__phone", "student__first_name", "student__last_name")
    list_select_related = ("student", "assignment", "assignment__lesson", "reviewer")
    date_hierarchy = "created_at"
    fields = (
        "student",
        "assignment",
        ("attempt", "status", "late"),
        "text",
        "show_code",
        "link",
        "show_files",
        ("score", "reviewer", "reviewed_at"),
        "feedback",
        "review_link",
        ("created_at", "updated_at"),
    )
    readonly_fields = (
        "student",
        "assignment",
        "attempt",
        "status",
        "late",
        "text",
        "show_code",
        "link",
        "show_files",
        "score",
        "reviewer",
        "reviewed_at",
        "feedback",
        "review_link",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Submission]:
        queryset = super().get_queryset(request)
        if sees_all(request.user):
            return queryset
        # O'qituvchi — faqat o'zi tekshiradigan javoblar.
        return queryset.filter(pk__in=services.reviewable(request.user).values("pk"))

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @display(
        description=_("Holat"),
        ordering="status",
        label={
            Submission.Status.SUBMITTED: "warning",
            Submission.Status.CHANGES_REQUESTED: "danger",
            Submission.Status.ACCEPTED: "success",
        },
    )
    def show_status(self, obj: Submission) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @admin.display(description=_("Kod"))
    def show_code(self, obj: Submission) -> str:
        if not obj.code:
            return "—"
        return format_html('<pre class="whitespace-pre-wrap overflow-auto">{}</pre>', obj.code)

    @admin.display(description=_("Fayllar"))
    def show_files(self, obj: Submission) -> str:
        items = [(services.file_payload(item)["url"], item.name) for item in obj.files.all()]
        if not items:
            return "—"
        return format_html_join(
            ", ", '<a href="{}" target="_blank" rel="noopener" class="underline">{}</a>', items
        )

    @admin.display(description=_("Kabinetda"))
    def review_link(self, obj: Submission) -> str:
        url = f"{settings.APP_URL.rstrip('/')}/uz/dashboard/reviews/{obj.pk}"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" class="underline">{}</a>',
            url,
            _("Tekshirish sahifasini ochish"),
        )
