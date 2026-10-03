from typing import Any

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import PlacementAttempt, PlacementTest


@admin.register(PlacementTest)
class PlacementTestAdmin(ModelAdmin):
    list_display = ("title", "course", "questions_count", "duration_min", "bank", "is_active")
    list_editable = ("is_active",)
    list_select_related = ("course", "quiz__lesson")
    autocomplete_fields = ("course", "quiz")
    fields = ("title", "course", "quiz", ("questions_count", "duration_min"), "is_active", "order")

    def get_queryset(self, request: HttpRequest) -> QuerySet[PlacementTest]:
        return super().get_queryset(request).annotate(bank_size=Count("quiz__questions"))

    @admin.display(description=_("savollar bankida"))
    def bank(self, obj: Any) -> int:
        return int(obj.bank_size)


@admin.register(PlacementAttempt)
class PlacementAttemptAdmin(ModelAdmin):
    list_display = ("user", "test", "score", "coupon", "started_at", "finished_at")
    list_filter = ("test", ("finished_at", admin.EmptyFieldListFilter))
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    list_select_related = ("user", "test", "coupon")
    fields = ("user", "test", "score", "coupon", "started_at", "deadline", "finished_at")
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
