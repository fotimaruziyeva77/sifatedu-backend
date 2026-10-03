"""Admin: XP va coin sozlamalari, tarix (qo'lda qo'shish, bekor qilish), hamyonlar, kunlik
topshiriqlar va kuponlar."""

import uuid
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm

from apps.core.admin_utils import ActionsOnlyChangeMixin
from apps.notifications.admin import finish

from . import services
from .models import Coupon, DailyTask, Entry, GameSettings, Wallet


@admin.register(GameSettings)
class GameSettingsAdmin(ModelAdmin):
    """Bitta yozuv: ro'yxat o'rniga to'g'ridan-to'g'ri tahrirlash sahifasi."""

    fieldsets = (
        (
            _("XP va coin (har harakat uchun; coin — XP ga teng)"),
            {
                "fields": (
                    ("lesson_xp", "quiz_xp"),
                    ("homework_xp", "attendance_xp"),
                    ("exam_xp", "daily_bonus_xp"),
                )
            },
        ),
        (
            _("Shtraflar (faqat XP, 0 dan pastga tushmaydi)"),
            {
                "fields": (
                    ("daily_missed_penalty", "absent_penalty"),
                    ("late_penalty", "homework_late_penalty"),
                )
            },
        ),
        (
            _("Do'stni taklif qilish"),
            {
                "fields": (
                    ("referral_lesson_coins", "referral_paid_coins"),
                    ("referral_discount", "coupon_percent"),
                )
            },
        ),
        (
            _("Daraja testi (botga yangi kelganlar)"),
            {
                "fields": (
                    ("placement_good_percent", "placement_coupon_hours"),
                    ("placement_high_coupon", "placement_low_coupon"),
                )
            },
        ),
        (_("Yoqish"), {"fields": ("daily_tasks", "announce_winners")}),
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def changelist_view(self, request: HttpRequest, extra_context: Any = None) -> HttpResponse:
        GameSettings.load()
        return HttpResponseRedirect(reverse("admin:rewards_gamesettings_change", args=[1]))


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ("user", "xp", "coins", "note")
        help_texts = {
            "xp": _("Musbat — qo'shish, manfiy — ayirish (0 dan pastga tushmaydi)."),
            "coins": _("Musbat — qo'shish, manfiy — ayirish."),
        }


class CancelForm(BaseDialogForm):
    reason = forms.CharField(label=_("Sabab"), max_length=300)


@admin.register(Entry)
class EntryAdmin(ActionsOnlyChangeMixin, ModelAdmin):
    form = EntryForm
    list_display = (
        "user",
        "show_reason",
        "applied_xp",
        "coins",
        "note",
        "created_at",
        "show_state",
    )
    list_filter = ("reason", ("canceled_at", admin.EmptyFieldListFilter))
    search_fields = ("user__phone", "user__first_name", "user__last_name", "note")
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    autocomplete_fields = ("user",)
    actions_detail = ("cancel_entry",)

    def get_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is None:
            return ("user", "xp", "coins", "note")
        return (
            "user",
            "reason",
            ("xp", "applied_xp", "coins"),
            "course",
            "note",
            "created_at",
            "created_by",
            ("canceled_at", "canceled_by"),
            "cancel_reason",
        )

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is None:
            return ()
        return (
            "user",
            "reason",
            "xp",
            "applied_xp",
            "coins",
            "course",
            "note",
            "created_at",
            "created_by",
            "canceled_at",
            "canceled_by",
            "cancel_reason",
        )

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_cancel_entry_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return request.user.has_perm("rewards.change_entry")

    def save_model(self, request: HttpRequest, obj: Entry, form: Any, change: bool) -> None:
        """Qo'lda: hamyon ham o'zgaradi (to'g'ridan-to'g'ri saqlanmaydi)."""
        if change:
            return
        try:
            entry = services.credit(
                obj.user_id,
                Entry.Reason.MANUAL,
                key=f"manual:{uuid.uuid4().hex}",
                xp=obj.xp,
                coins=obj.coins,
                note=obj.note,
                by=request.user,
            )
        except services.RewardError as exc:
            messages.error(request, str(exc))
            return
        if entry is not None:
            obj.pk = entry.pk

    @display(description=_("Sabab"), label=True)
    def show_reason(self, obj: Entry) -> str:
        return obj.get_reason_display()

    @display(description=_("Holat"), label={True: "danger", False: "success"})
    def show_state(self, obj: Entry) -> tuple[bool, str]:
        canceled = obj.canceled_at is not None
        return canceled, str(_("Bekor qilingan") if canceled else _("Faol"))

    @action(
        description=_("Bekor qilish"),
        url_path="cancel",
        permissions=["cancel_entry"],
        icon="undo",
        variant=ActionVariant.DANGER,
        dialog={
            "title": _("Yozuvni bekor qilish"),
            "description": _("XP va coin o'quvchiga qaytariladi (yoki qayta yechiladi)."),
            "form_class": CancelForm,
            "form_submit_text": _("Bekor qilish"),
        },
    )
    def cancel_entry(self, request: HttpRequest, form: Any, object_id: int) -> HttpResponse:
        entry = get_object_or_404(Entry, pk=object_id)
        reason = str(form.cleaned_data.get("reason") or "") if form is not None else ""
        try:
            services.cancel(entry, by=request.user, reason=reason)
            messages.success(request, _("Yozuv bekor qilindi."))
        except services.RewardError as exc:
            messages.error(request, str(exc))
        return finish(request, reverse("admin:rewards_entry_change", args=[object_id]))


@admin.register(Wallet)
class WalletAdmin(ActionsOnlyChangeMixin, ModelAdmin):
    list_display = ("user", "xp", "coins", "streak", "best_streak", "hidden")
    list_filter = ("hidden",)
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    list_select_related = ("user",)
    ordering = ("-xp",)
    readonly_fields = ("user", "xp", "coins", "streak", "best_streak", "streak_day", "hidden")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(DailyTask)
class DailyTaskAdmin(ActionsOnlyChangeMixin, ModelAdmin):
    list_display = ("user", "day", "kind", "title", "done_at")
    list_filter = ("day", "kind", ("done_at", admin.EmptyFieldListFilter))
    search_fields = ("user__phone", "user__first_name", "title")
    list_select_related = ("user",)
    readonly_fields = (
        "user",
        "day",
        "kind",
        "course",
        "lesson",
        "quiz",
        "assignment",
        "live_lesson",
        "title",
        "done_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ("user", "percent", "kind", "expires_at", "friend", "created_at", "used_at")
    list_filter = ("kind", ("used_at", admin.EmptyFieldListFilter))
    search_fields = ("user__phone", "user__first_name")
    list_select_related = ("user", "friend")
    autocomplete_fields = ("user",)
    fields = ("user", "percent", "kind", "expires_at", "friend", "order", "created_at", "used_at")
    readonly_fields = ("friend", "order", "created_at", "used_at")

    def get_changeform_initial_data(self, request: HttpRequest) -> dict[str, Any]:
        # Admin'da yaratilgan kupon — qo'lda berilgan.
        return {**super().get_changeform_initial_data(request), "kind": Coupon.Kind.MANUAL}

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
