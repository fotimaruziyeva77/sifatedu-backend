"""Platforma paneli (super admin): faqat platforma manzilida ochiladi (`config/urls_public.py`).

Markazlarning o'z admin paneli — alohida (`admin.site`), u bu yerdagi modellarni ko'rmaydi.
"""

from typing import Any

from django import forms
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.defaultfilters import filesizeformat
from django_tenants.utils import get_public_schema_name
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.sites import UnfoldAdminSite
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget

from .models import Center, Domain, Plan
from .sections import Feature


class PlatformAdminSite(UnfoldAdminSite):
    settings_name = "UNFOLD_PLATFORM"


# `name="admin"`: Unfold shablonlari `admin:` nomlari bilan ishlaydi.
platform_site = PlatformAdminSite(name="admin")


def feature_field(label: str, help_text: str) -> forms.MultipleChoiceField:
    return forms.MultipleChoiceField(
        label=label,
        help_text=help_text,
        choices=Feature.choices,
        required=False,
        widget=UnfoldAdminCheckboxSelectMultipleWidget,
    )


class PlanForm(forms.ModelForm):
    features = feature_field(
        "Bo'limlar",
        "O'quvchilar, guruhlar, jadval, davomat, arizalar va sayt hamma tarifda ochiq.",
    )


@admin.register(Plan, site=platform_site)
class PlanAdmin(ModelAdmin):
    form = PlanForm
    list_display = ("name", "price", "sections", "max_students", "max_staff", "max_disk_gb")
    ordering = ("order", "id")

    @display(description="Bo'limlar")
    def sections(self, obj: Plan) -> str:
        return f"{len(obj.features)} / {len(Feature)}"


class DomainForm(forms.ModelForm):
    class Meta:
        labels = {"domain": "Manzil", "is_primary": "Asosiy"}


class DomainInline(TabularInline):
    model = Domain
    form = DomainForm
    extra = 1
    fields = ("domain", "is_primary")


class CenterForm(forms.ModelForm):
    extra_features = feature_field(
        "Qo'shimcha bo'limlar", "Tarifga kirmagan bo'limni shu markazga alohida ochadi."
    )

    class Meta:
        labels = {"schema_name": "Sxema"}
        help_texts = {
            "schema_name": "Bazadagi nomi: lotin harflari va raqamlar. Keyin o'zgarmaydi."
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            self.fields["plan"].required = True


SETTINGS_FIELDS = ("plan", "extra_features", "paid_until", "is_suspended")
USAGE_FIELDS = ("students_count", "staff_count", "disk")


@admin.register(Center, site=platform_site)
class CenterAdmin(ModelAdmin):
    form = CenterForm
    list_display = ("name", "schema", "address", "plan", "status", "paid_until", *USAGE_FIELDS)
    list_filter = ("plan", "is_suspended")
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

    @display(
        description="Holat",
        label={
            Center.State.ACTIVE: "success",
            Center.State.GRACE: "warning",
            Center.State.BLOCKED: "danger",
        },
    )
    def status(self, obj: Center) -> tuple[str, str]:
        state = Center.State(obj.state)
        return state.value, str(state.label)

    @display(description="Disk", ordering="disk_bytes")
    def disk(self, obj: Center) -> str:
        return filesizeformat(obj.disk_bytes)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Center]:
        queryset = super().get_queryset(request)
        return (
            queryset.exclude(schema_name=get_public_schema_name())
            .select_related("plan")
            .prefetch_related("domains")
        )

    def get_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        if obj is None:
            return ("name", "schema_name", *SETTINGS_FIELDS)
        return ("name", "schema", *SETTINGS_FIELDS, *USAGE_FIELDS)

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        return ("schema", *USAGE_FIELDS) if obj else ()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
