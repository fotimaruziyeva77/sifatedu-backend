from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import DailyAttempt, DailyTest


@admin.register(DailyTest)
class DailyTestAdmin(ModelAdmin):
    list_display = ("day", "group", "status", "questions_count", "pool_size", "attempts_done")
    list_filter = ("status", "day", "group")
    search_fields = ("group__name",)
    list_select_related = ("group",)
    date_hierarchy = "day"
    fields = (
        ("group", "day"),
        ("status", "questions_count", "pool_size"),
        ("opens_at", "closes_at"),
    )
    readonly_fields = (
        "group",
        "day",
        "status",
        "questions_count",
        "pool_size",
        "opens_at",
        "closes_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @admin.display(description=_("ishladi"))
    def attempts_done(self, obj: DailyTest) -> int:
        return obj.attempts.filter(finished_at__isnull=False).count()


@admin.register(DailyAttempt)
class DailyAttemptAdmin(ModelAdmin):
    list_display = ("student", "test", "correct", "total", "started_at", "finished_at")
    list_filter = ("test__day", "test__group")
    search_fields = ("student__phone", "student__first_name", "student__last_name")
    list_select_related = ("student", "test__group")
    fields = ("student", "test", ("correct", "total"), ("started_at", "finished_at"))
    readonly_fields = ("student", "test", "correct", "total", "started_at", "finished_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
