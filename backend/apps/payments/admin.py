from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.core.admin_utils import FORMFIELD_OVERRIDES

from .models import Order, PaymentLog, PaymentTransaction, Refund


class TransactionInline(TabularInline):
    """Buyurtma sahifasida uning tranzaksiyalari."""

    model = PaymentTransaction
    formfield_overrides = FORMFIELD_OVERRIDES
    extra = 0
    can_delete = False
    fields = ("provider_trans_id", "status", "amount", "fiscal_receipt_url", "confirmed_at")
    readonly_fields = ("provider_trans_id", "status", "amount", "confirmed_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    """Buyurtmalar. Holat to'lov tizimidan keladi, qo'lda o'zgartirilmaydi."""

    list_display = ("__str__", "user", "show_status", "show_format", "show_amount", "created_at")
    list_filter = ("status", "study_format", "provider", "course")
    search_fields = ("id", "user__phone", "user__first_name", "course__title")
    date_hierarchy = "created_at"
    raw_id_fields = ("user",)
    autocomplete_fields = ("course",)
    inlines = [TransactionInline]
    readonly_fields = (
        "user",
        "course",
        "study_format",
        "months",
        "amount",
        "status",
        "provider",
        "paid_at",
        "created_at",
        "updated_at",
    )
    fieldsets = [
        (None, {"fields": ["user", "course", ("study_format", "months"), "amount"]}),
        (_("Holat"), {"fields": [("status", "provider"), "paid_at"]}),
        (_("Vaqt"), {"fields": [("created_at", "updated_at")]}),
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Order]:
        return super().get_queryset(request).select_related("user", "course")

    def has_add_permission(self, request: HttpRequest) -> bool:
        # Buyurtma saytda yaratiladi. Qo'lda kirish berish — "Kursga yozilishlar" bo'limida.
        return False

    @display(
        description=_("Holat"),
        label={
            Order.Status.NEW: "warning",
            Order.Status.PAID: "success",
            Order.Status.EXPIRED: "info",
            Order.Status.CANCELLED: "danger",
            Order.Status.REFUNDED: "danger",
        },
    )
    def show_status(self, obj: Order) -> tuple[str, str]:
        return obj.status, str(obj.get_status_display())

    @display(description=_("Shakl"), ordering="study_format")
    def show_format(self, obj: Order) -> str:
        if obj.study_format == Order.Format.OFFLINE:
            return f"{obj.get_study_format_display()} · {obj.months} oy"
        return str(obj.get_study_format_display())

    @display(description=_("Summa"), ordering="amount")
    def show_amount(self, obj: Order) -> str:
        return f"{obj.amount:,} so'm".replace(",", " ")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    """Faqat ko'rish uchun. Fiskal chek havolasini qo'lda kiritish mumkin."""

    formfield_overrides = FORMFIELD_OVERRIDES
    list_display = ("provider_trans_id", "order", "show_status", "amount", "confirmed_at")
    list_filter = ("status", "provider")
    search_fields = ("provider_trans_id", "paydoc_id", "order__id")
    date_hierarchy = "created_at"
    readonly_fields = (
        "order",
        "provider",
        "provider_trans_id",
        "paydoc_id",
        "amount",
        "status",
        "confirmed_at",
        "cancelled_at",
        "created_at",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[PaymentTransaction]:
        return super().get_queryset(request).select_related("order", "order__course")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @display(
        description=_("Holat"),
        label={
            PaymentTransaction.Status.PREPARED: "warning",
            PaymentTransaction.Status.CONFIRMED: "success",
            PaymentTransaction.Status.CANCELLED: "danger",
        },
    )
    def show_status(self, obj: PaymentTransaction) -> tuple[str, str]:
        return obj.status, str(obj.get_status_display())


@admin.register(PaymentLog)
class PaymentLogAdmin(ModelAdmin):
    """To'lov tizimi bilan yozishmalar: muammo chiqqanda shu yerdan qaraladi."""

    list_display = ("created_at", "provider", "action", "order", "show_error")
    list_filter = ("provider", "action")
    search_fields = ("order__id",)
    date_hierarchy = "created_at"
    readonly_fields = ("provider", "action", "order", "request", "response", "ip", "created_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @display(description=_("Natija"))
    def show_error(self, obj: PaymentLog) -> str:
        code = obj.response.get("error") if isinstance(obj.response, dict) else None
        if code is None:
            return "—"
        return "OK" if code == 0 else f"{code}: {obj.response.get('error_note', '')}"


@admin.register(Refund)
class RefundAdmin(ModelAdmin):
    """Pul Click kabinetida qaytariladi, bu yerda faqat qayd etiladi."""

    list_display = ("order", "show_amount", "show_status", "decided_by", "decided_at")
    list_filter = ("status",)
    search_fields = ("order__id", "order__user__phone")
    date_hierarchy = "created_at"
    raw_id_fields = ("order",)
    actions = ("mark_done",)
    readonly_fields = ("decided_by", "decided_at", "created_at")
    fieldsets = [
        (None, {"fields": ["order", "amount", "reason"]}),
        (_("Qaror"), {"fields": ["status", "note", ("decided_by", "decided_at")]}),
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Refund]:
        return super().get_queryset(request).select_related("order", "decided_by")

    def save_model(self, request: HttpRequest, obj: Refund, form: Any, change: bool) -> None:
        # Qaror qabul qilinganda kim va qachon qilgani avtomatik yoziladi.
        if obj.status != Refund.Status.REQUESTED and obj.decided_at is None:
            obj.decided_by = request.user if request.user.is_authenticated else None
            obj.decided_at = timezone.now()
        super().save_model(request, obj, form, change)
        if obj.status == Refund.Status.DONE:
            self._close_order(obj)

    @admin.action(description=_("Pul qaytarildi deb belgilash"))
    def mark_done(self, request: HttpRequest, queryset: QuerySet[Refund]) -> None:
        count = 0
        for refund in queryset.exclude(status=Refund.Status.DONE):
            refund.status = Refund.Status.DONE
            refund.decided_by = request.user if request.user.is_authenticated else None
            refund.decided_at = timezone.now()
            refund.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
            self._close_order(refund)
            count += 1
        self.message_user(
            request,
            _("%d ta pul qaytarish belgilandi.") % count,
            messages.SUCCESS if count else messages.WARNING,
        )

    def _close_order(self, refund: Refund) -> None:
        """Pul qaytgach buyurtma yopiladi va kursga kirish bekor qilinadi."""
        from apps.learning.models import Enrollment

        order = refund.order
        if order.status != Order.Status.REFUNDED:
            order.status = Order.Status.REFUNDED
            order.save(update_fields=["status", "updated_at"])
        Enrollment.objects.filter(user=order.user, course=order.course).update(
            status=Enrollment.Status.CANCELLED, updated_at=timezone.now()
        )

    @display(description=_("Summa"), ordering="amount")
    def show_amount(self, obj: Refund) -> str:
        return f"{obj.amount:,} so'm".replace(",", " ")

    @display(
        description=_("Holat"),
        label={
            Refund.Status.REQUESTED: "warning",
            Refund.Status.APPROVED: "info",
            Refund.Status.REJECTED: "danger",
            Refund.Status.DONE: "success",
        },
    )
    def show_status(self, obj: Refund) -> tuple[str, str]:
        return obj.status, str(obj.get_status_display())
