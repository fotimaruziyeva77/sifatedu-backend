"""Platforma paneli (super admin): faqat platforma manzilida ochiladi (`config/urls_public.py`).

Markazlarning o'z admin paneli — alohida (`admin.site`), u bu yerdagi modellarni ko'rmaydi.
"""

from typing import Any

from django import forms
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django_tenants.utils import get_public_schema_name
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.sites import UnfoldAdminSite

from .models import Center, Domain


class PlatformAdminSite(UnfoldAdminSite):
    settings_name = "UNFOLD_PLATFORM"


# `name="admin"`: Unfold shablonlari `admin:` nomlari bilan ishlaydi.
platform_site = PlatformAdminSite(name="admin")


class DomainForm(forms.ModelForm):
    class Meta:
        labels = {"domain": "Manzil", "is_primary": "Asosiy"}


class DomainInline(TabularInline):
    model = Domain
    form = DomainForm
    extra = 1
    fields = ("domain", "is_primary")


class CenterForm(forms.ModelForm):
    class Meta:
        labels = {"schema_name": "Sxema"}
        help_texts = {
            "schema_name": "Bazadagi nomi: lotin harflari va raqamlar. Keyin o'zgarmaydi."
        }


@admin.register(Center, site=platform_site)
class CenterAdmin(ModelAdmin):
    form = CenterForm
    list_display = ("name", "schema", "address", "created_at")
    search_fields = ("name", "schema_name", "domains__domain")
    ordering = ("-created_at",)
    inlines = (DomainInline,)

    @display(description="Sxema", ordering="schema_name")
    def schema(self, obj: Center) -> str:
        return obj.schema_name

    @display(description="Manzil")
    def address(self, obj: Center) -> str:
        primary = next((item for item in obj.domains.all() if item.is_primary), None)
        return primary.domain if primary else "—"

    def get_queryset(self, request: HttpRequest) -> QuerySet[Center]:
        queryset = super().get_queryset(request)
        return queryset.exclude(schema_name=get_public_schema_name()).prefetch_related("domains")

    def get_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        return ("name", "schema") if obj else ("name", "schema_name")

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        return ("schema",) if obj else ()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
