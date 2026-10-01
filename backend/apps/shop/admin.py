"""Admin: sovg'alar va buyurtmalar (holat: tayyor → topshirildi yoki bekor — coin qaytadi)."""

from typing import Any

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm

from apps.core.admin_utils import ActionsOnlyChangeMixin, TranslatedModelAdmin, language_tabs
from apps.notifications.admin import finish

from . import services
from .models import Product, Purchase

Status = Purchase.Status


@admin.register(Product)
class ProductAdmin(TranslatedModelAdmin):
    list_display = ("name", "price", "kind", "show_stock", "audience", "is_active", "order")
    list_editable = ("is_active", "order")
    list_filter = ("is_active", "kind", "audience")
    search_fields = ("name_uz", "name_ru", "name_en")
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "image",
                    ("price", "stock"),
                    ("kind", "audience"),
                    ("is_active", "order"),
                ],
                "description": _(
                    "Narx — coin. Zaxira bo'sh — cheksiz; tugasa sovg'a do'konda ko'rinmaydi."
                ),
            },
        ),
        *language_tabs(("name", "description")),
    ]

    @admin.display(description=_("Zaxira"))
    def show_stock(self, obj: Product) -> str:
        return "∞" if obj.stock is None else str(obj.stock)


class NoteForm(BaseDialogForm):
    note = forms.CharField(
        label=_("Izoh o'quvchiga"),
        max_length=300,
        required=False,
        help_text=_("Masalan: «Ertaga 14:00 da ofisdan olib keting»."),
    )


class CancelForm(BaseDialogForm):
    note = forms.CharField(label=_("Sabab (o'quvchiga boradi)"), max_length=300)


@admin.register(Purchase)
class PurchaseAdmin(ActionsOnlyChangeMixin, ModelAdmin):
    list_display = ("name", "user", "price", "show_status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "user__phone", "user__first_name", "user__last_name")
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    fields = (
        "user",
        "product",
        "name",
        "price",
        "status",
        "note",
        "created_at",
        ("ready_at", "delivered_at", "canceled_at"),
        "handled_by",
    )
    readonly_fields = (
        "user",
        "product",
        "name",
        "price",
        "status",
        "note",
        "created_at",
        "ready_at",
        "delivered_at",
        "canceled_at",
        "handled_by",
    )
    actions_detail = ("mark_ready", "mark_delivered", "cancel_purchase")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def _can(self, request: HttpRequest, object_id: Any, status: str) -> bool:
        if not request.user.has_perm("shop.change_purchase"):
            return False
        if object_id is None:
            return True
        purchase = Purchase.objects.filter(pk=object_id).only("status").first()
        return purchase is not None and status in services.FLOW[Status(purchase.status)]

    def has_mark_ready_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._can(request, object_id, Status.READY)

    def has_mark_delivered_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._can(request, object_id, Status.DELIVERED)

    def has_cancel_purchase_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._can(request, object_id, Status.CANCELED)

    @display(
        description=_("Holat"),
        label={
            Status.NEW: "warning",
            Status.READY: "info",
            Status.DELIVERED: "success",
            Status.CANCELED: "danger",
        },
    )
    def show_status(self, obj: Purchase) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    def change(
        self, request: HttpRequest, object_id: int, status: str, note: str | None
    ) -> HttpResponse:
        purchase = get_object_or_404(Purchase, pk=object_id)
        try:
            services.set_status(purchase, status, by=request.user, note=note)
            messages.success(request, _("Buyurtma holati o'zgardi, o'quvchiga xabar ketdi."))
        except services.ShopError as exc:
            messages.error(request, str(exc))
        return finish(request, reverse("admin:shop_purchase_change", args=[object_id]))

    @action(
        description=_("Tayyor"),
        url_path="ready",
        permissions=["mark_ready"],
        icon="inventory_2",
        dialog={
            "title": _("Sovg'a tayyor"),
            "description": _("O'quvchiga «tayyor» xabari boradi."),
            "form_class": NoteForm,
            "form_submit_text": _("Tayyor"),
        },
    )
    def mark_ready(self, request: HttpRequest, form: Any, object_id: int) -> HttpResponse:
        note = str(form.cleaned_data.get("note") or "") if form is not None else ""
        return self.change(request, object_id, Status.READY, note or None)

    @action(
        description=_("Topshirildi"),
        url_path="delivered",
        permissions=["mark_delivered"],
        icon="task_alt",
        variant=ActionVariant.SUCCESS,
    )
    def mark_delivered(self, request: HttpRequest, object_id: int) -> HttpResponse:
        return self.change(request, object_id, Status.DELIVERED, None)

    @action(
        description=_("Bekor qilish"),
        url_path="cancel",
        permissions=["cancel_purchase"],
        icon="undo",
        variant=ActionVariant.DANGER,
        dialog={
            "title": _("Buyurtmani bekor qilish"),
            "description": _("Coin o'quvchiga qaytadi, zaxira tiklanadi."),
            "form_class": CancelForm,
            "form_submit_text": _("Bekor qilish"),
        },
    )
    def cancel_purchase(self, request: HttpRequest, form: Any, object_id: int) -> HttpResponse:
        note = str(form.cleaned_data.get("note") or "") if form is not None else ""
        return self.change(request, object_id, Status.CANCELED, note)
