"""Admin: o'quvchilarga xabar yuborish va yuborilgan xabarlar (faqat ko'rish)."""

from typing import Any

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm

from apps.users.models import User

from . import services
from .models import Broadcast, Delivery, Notification

EDITABLE_WHILE_DRAFT = (
    "title",
    "body",
    "link",
    "image",
    "kind",
    "audience",
    "courses",
    "groups",
    "without_course",
    "joined_from",
    "joined_to",
    "send_telegram",
    "bot_all",
    "send_sms",
    "sms_text",
)
FILTERS = ("courses", "groups", "without_course", "joined_from", "joined_to")


class BroadcastForm(forms.ModelForm):
    class Meta:
        model = Broadcast
        fields = EDITABLE_WHILE_DRAFT

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("without_course") and (cleaned.get("courses") or cleaned.get("groups")):
            raise ValidationError(
                {
                    "without_course": _(
                        "Kurs yoki guruh tanlangan — «faqat kurs tanlamaganlar» bilan birga "
                        "bo'lmaydi."
                    )
                }
            )
        if cleaned.get("bot_all"):
            # Bot foydalanuvchisining kursi va kabineti noma'lum: filtr ularga qo'llanmaydi.
            filtered = cleaned.get("audience") != Broadcast.Audience.ALL or any(
                cleaned.get(name) for name in FILTERS
            )
            if filtered:
                raise ValidationError(
                    {"bot_all": _("«Botdagi hammaga» faqat filtrsiz xabarda ishlaydi.")}
                )
            if not cleaned.get("send_telegram"):
                raise ValidationError(
                    {"bot_all": _("«Botdagi hammaga» uchun Telegram belgilangan bo'lsin.")}
                )
        return cleaned


class SendDialogForm(BaseDialogForm):
    """Tasdiqlash oynasi: xabar kimga qaysi kanal orqali yetishi va SMS narxi."""

    form_before_template = "notifications/send_summary.html"

    def get_before_template_context(
        self, request: HttpRequest, object_id: int | str | None = None
    ) -> dict[str, Any]:
        broadcast = Broadcast.objects.filter(pk=object_id).first() if object_id else None
        if broadcast is None:
            return {}
        return {
            "reach": services.reach(broadcast),
            "night": (broadcast.kind == Broadcast.Kind.PROMO or broadcast.bot_all)
            and services.in_quiet_hours(timezone.now()),
        }


def finish(request: HttpRequest, url: str) -> HttpResponse:
    """Dialog htmx orqali yuboriladi: sahifani to'liq yangilash uchun `HX-Redirect`."""
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=200)
        response["HX-Redirect"] = url
        return response
    return HttpResponseRedirect(url)


@admin.register(Broadcast)
class BroadcastAdmin(ModelAdmin):
    form = BroadcastForm
    list_display = (
        "title",
        "show_kind",
        "show_status",
        "recipients",
        "show_delivery",
        "sent_at",
        "created_by",
    )
    list_filter = ("status", "kind")
    search_fields = ("title", "body")
    autocomplete_fields = ("courses", "groups")
    list_select_related = ("created_by",)
    date_hierarchy = "created_at"
    warn_unsaved_form = True
    readonly_fields = ("status", "created_by", "scheduled_for", "sent_at", "recipients", "results")
    fieldsets = (
        (_("Xabar"), {"fields": ("title", "body", "link", "image", "kind")}),
        (
            _("Kimga"),
            {
                "description": _(
                    "Faol o'quvchilar (xodimlar emas). Filtrlar birga ishlaydi: masalan, "
                    "«Kids» va kurs — shu kursdagi bolalar."
                ),
                "fields": (
                    "audience",
                    ("courses", "groups"),
                    "without_course",
                    ("joined_from", "joined_to"),
                ),
            },
        ),
        (
            _("Kanallar"),
            {
                "description": _(
                    "Kabinetdagi «Xabarlar» bo'limiga har doim yoziladi. Telegram bepul; "
                    "SMS — faqat Telegram'i yo'qlarga. «Botdagi hammaga» — yangiliklar "
                    "botga /start bosgan hammaga (ro'yxatdan o'tmaganlarga ham)."
                ),
                "fields": (("send_telegram", "bot_all"), "send_sms", "sms_text"),
            },
        ),
        (
            _("Natija"),
            {"fields": ("status", ("scheduled_for", "sent_at"), "created_by", "results")},
        ),
    )
    actions_detail = ("send_now", "send_test")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Broadcast]:
        return (
            super()
            .get_queryset(request)
            .annotate(
                telegram_sent=Count(
                    "notifications", filter=Q(notifications__telegram=Delivery.SENT)
                ),
                sms_sent=Count("notifications", filter=Q(notifications__sms=Delivery.SENT)),
                failed=Count(
                    "notifications",
                    filter=Q(notifications__telegram=Delivery.FAILED)
                    | Q(notifications__sms=Delivery.FAILED),
                ),
            )
        )

    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        # Yangi xabarda "Natija" bo'sh — ko'rsatilmaydi.
        return self.fieldsets if obj is not None else self.fieldsets[:-1]

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        # Yuborilgan xabar o'zgarmaydi: o'quvchilar aynan shu matnni olgan.
        if obj is not None and not obj.is_draft:
            return (*EDITABLE_WHILE_DRAFT, *self.readonly_fields)
        return self.readonly_fields

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        # Yuborilgani o'chirilsa, o'quvchilarning kabinetidagi xabarlar ham o'chib ketardi.
        if obj is not None and not obj.is_draft:
            return False
        return super().has_delete_permission(request, obj)

    def has_send_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if not request.user.has_perm("notifications.send_broadcast"):
            return False
        if object_id is None:
            return True
        return Broadcast.objects.filter(pk=object_id, status=Broadcast.Status.DRAFT).exists()

    def save_model(self, request: HttpRequest, obj: Broadcast, form: Any, change: bool) -> None:
        if not change and isinstance(request.user, User):
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @display(
        description=_("Turi"),
        label={Broadcast.Kind.INFO: "info", Broadcast.Kind.PROMO: "warning"},
    )
    def show_kind(self, obj: Broadcast) -> tuple[str, str]:
        return obj.kind, obj.get_kind_display()

    @display(
        description=_("Holat"),
        label={
            Broadcast.Status.DRAFT: "info",
            Broadcast.Status.SCHEDULED: "warning",
            Broadcast.Status.SENT: "success",
        },
    )
    def show_status(self, obj: Broadcast) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @admin.display(description=_("Telegram / SMS / yetmadi"))
    def show_delivery(self, obj: Broadcast) -> str:
        if obj.is_draft:
            return "—"
        return f"{obj.telegram_sent} / {obj.sms_sent} / {obj.failed}"  # type: ignore[attr-defined]

    @admin.display(description=_("Yetkazish"))
    def results(self, obj: Broadcast) -> str:
        if obj.pk is None or obj.is_draft:
            return str(_("Yuborilgandan keyin shu yerda natija chiqadi."))
        rows = obj.notifications.aggregate(
            read=Count("pk", filter=Q(read_at__isnull=False)),
            telegram=Count("pk", filter=Q(telegram=Delivery.SENT)),
            sms=Count("pk", filter=Q(sms=Delivery.SENT)),
            queued=Count("pk", filter=Q(telegram=Delivery.QUEUED) | Q(sms=Delivery.QUEUED)),
            failed=Count("pk", filter=Q(telegram=Delivery.FAILED) | Q(sms=Delivery.FAILED)),
        )
        summary = format_html(
            "{}: <b>{}</b> · {}: <b>{}</b> · SMS: <b>{}</b> · {}: <b>{}</b> · {}: <b>{}</b> · "
            "{}: <b>{}</b>",
            _("Qabul qiluvchilar"),
            obj.recipients,
            "Telegram",
            rows["telegram"],
            rows["sms"],
            _("navbatda"),
            rows["queued"],
            _("yetmadi"),
            rows["failed"],
            _("kabinetda o'qidi"),
            rows["read"],
        )
        if not obj.bot_all:
            return summary
        return format_html(
            "{}<br>{}: <b>{}</b> · {}: <b>{}</b> · {}: <b>{}</b>",
            summary,
            _("Bot foydalanuvchilari"),
            obj.bot_recipients,
            _("yetdi"),
            obj.bot_sent,
            _("yetmadi"),
            obj.bot_failed,
        )

    @action(
        description=_("Yuborish"),
        url_path="send",
        permissions=["send"],
        icon="send",
        variant=ActionVariant.PRIMARY,
        dialog={
            "title": _("Xabarni yuborish"),
            "description": _("Yuborilgan xabarni qaytarib bo'lmaydi. Raqamlarni tekshiring."),
            "form_class": SendDialogForm,
            "form_submit_text": _("Ha, yuborish"),
        },
    )
    def send_now(self, request: HttpRequest, form: Any, object_id: int) -> HttpResponse:
        broadcast = get_object_or_404(Broadcast, pk=object_id)
        url = reverse("admin:notifications_broadcast_change", args=[broadcast.pk])
        if not broadcast.is_draft:
            messages.error(request, _("Bu xabar allaqachon yuborilgan."))
            return finish(request, url)
        total = services.recipients(broadcast).count()
        if not total:
            messages.error(request, _("Filtrlarga mos o'quvchi yo'q — xabar yuborilmadi."))
            return finish(request, url)
        later = services.schedule(broadcast, request.user)  # type: ignore[arg-type]
        if later:
            messages.warning(
                request,
                _("Aksiya tungi vaqtda yuborilmaydi: %(time)s da ketadi.")
                % {"time": formats.date_format(timezone.localtime(later), "j E, H:i")},
            )
        else:
            messages.success(
                request, _("Xabar yuborilmoqda: %(total)s kishiga.") % {"total": total}
            )
        return finish(request, url)

    @action(
        description=_("Menga sinov"),
        url_path="test",
        permissions=["send"],
        icon="science",
        dialog={
            "title": _("Sinov xabari"),
            "description": _(
                "Xuddi shu xabar faqat sizga boradi: kabinetingizga va Telegram'ga (ulangan "
                "bo'lsa). O'quvchilarga yuborilmaydi."
            ),
            "form_submit_text": _("Menga yuborish"),
        },
    )
    def send_test(self, request: HttpRequest, form: Any, object_id: int) -> HttpResponse:
        broadcast = get_object_or_404(Broadcast, pk=object_id)
        services.send_test(broadcast, request.user)  # type: ignore[arg-type]
        messages.success(request, _("Sinov xabari sizga yuborildi."))
        return finish(request, reverse("admin:notifications_broadcast_change", args=[object_id]))


class DeliveryFilter(admin.SimpleListFilter):
    title = _("yetkazish")
    parameter_name = "delivery"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        return [
            ("failed", str(_("Yetmadi"))),
            ("queued", str(_("Navbatda"))),
            ("telegram", str(_("Telegram'ga yetdi"))),
            ("sms", str(_("SMS ketdi"))),
            ("site", str(_("Faqat kabinetda"))),
        ]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Notification]
    ) -> QuerySet[Notification]:
        value = self.value()
        if value == "failed":
            return queryset.filter(Q(telegram=Delivery.FAILED) | Q(sms=Delivery.FAILED))
        if value == "queued":
            return queryset.filter(Q(telegram=Delivery.QUEUED) | Q(sms=Delivery.QUEUED))
        if value == "telegram":
            return queryset.filter(telegram=Delivery.SENT)
        if value == "sms":
            return queryset.filter(sms=Delivery.SENT)
        if value == "site":
            return queryset.filter(telegram="", sms="")
        return queryset


DELIVERY_LABELS = {
    Delivery.QUEUED: "warning",
    Delivery.SENT: "success",
    Delivery.FAILED: "danger",
    "": "info",
}


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    """Kim qaysi xabarni oldi: kabinet, Telegram, SMS. Faqat ko'rish."""

    list_display = (
        "title",
        "user",
        "show_kind",
        "show_telegram",
        "show_sms",
        "show_read",
        "created_at",
    )
    list_filter = (DeliveryFilter, "kind")
    search_fields = ("title", "user__phone", "user__first_name", "user__last_name")
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    fields = (
        "user",
        "kind",
        "broadcast",
        "title",
        "body",
        "link",
        "created_at",
        "read_at",
        ("telegram", "sms"),
        "sms_text",
        "error",
    )
    readonly_fields = (
        "user",
        "kind",
        "broadcast",
        "title",
        "body",
        "link",
        "created_at",
        "read_at",
        "telegram",
        "sms",
        "sms_text",
        "error",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @display(description=_("Turi"), ordering="kind")
    def show_kind(self, obj: Notification) -> str:
        return obj.get_kind_display()

    @display(description="Telegram", label=DELIVERY_LABELS)
    def show_telegram(self, obj: Notification) -> tuple[str, str]:
        return obj.telegram, obj.get_telegram_display() if obj.telegram else "—"

    @display(description="SMS", label=DELIVERY_LABELS)
    def show_sms(self, obj: Notification) -> tuple[str, str]:
        return obj.sms, obj.get_sms_display() if obj.sms else "—"

    @display(description=_("O'qidi"), boolean=True, ordering="read_at")
    def show_read(self, obj: Notification) -> bool:
        return obj.read_at is not None
