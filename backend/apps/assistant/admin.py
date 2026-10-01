import json
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from . import budget
from .models import AssistantSettings, Conversation, Message


@admin.register(AssistantSettings)
class AssistantSettingsAdmin(ModelAdmin):
    fieldsets = [
        (None, {"fields": ["enabled", "knowledge"]}),
        (
            _("Budjet va limitlar"),
            {
                "fields": [
                    ("daily_budget_usd", "monthly_budget_usd"),
                    "max_user_messages",
                    "spending",
                ]
            },
        ),
    ]
    readonly_fields = ["spending"]
    warn_unsaved_form = True

    @admin.display(description=_("Xarajat"))
    def spending(self, obj: AssistantSettings) -> str:
        today = budget.spent_since(budget.day_start())
        month = budget.spent_since(budget.month_start())
        return (
            f"Bugun: ${today:.2f} / ${obj.daily_budget_usd:.2f} · "
            f"Shu oy: ${month:.2f} / ${obj.monthly_budget_usd:.2f}"
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not AssistantSettings.objects.exists()

    def has_delete_permission(
        self, request: HttpRequest, obj: AssistantSettings | None = None
    ) -> bool:
        return False

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, object] | None = None
    ) -> HttpResponse:
        # Yagona yozuv: ro'yxat o'rniga darhol tahrirlash sahifasi ochiladi (ruxsat bo'lsa).
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        obj = AssistantSettings.load()
        return redirect(reverse("admin:assistant_assistantsettings_change", args=[obj.pk]))


class BadRatingFilter(admin.SimpleListFilter):
    title = _("baho")
    parameter_name = "rating"

    def lookups(self, request: HttpRequest, model_admin: ModelAdmin) -> list[tuple[str, str]]:
        return [("bad", "👎"), ("good", "👍")]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Conversation]
    ) -> QuerySet[Conversation]:
        if self.value() == "bad":
            return queryset.filter(messages__rating=Message.Rating.BAD).distinct()
        if self.value() == "good":
            return queryset.filter(messages__rating=Message.Rating.GOOD).distinct()
        return queryset


@admin.register(Conversation)
class ConversationAdmin(ModelAdmin):
    """AI suhbatlari: menejer transkriptni o'qiydi, ariza bilan ishlaydi va suhbatni yopadi."""

    list_display = (
        "__str__",
        "show_channel",
        "show_status",
        "contact",
        "user_messages",
        "lead_link",
        "show_cost",
        "last_message_at",
    )
    list_filter = ("status", "channel", BadRatingFilter, "locale", "last_message_at")
    list_filter_submit = True
    search_fields = ("id", "name", "telegram_username", "lead__phone", "messages__text")
    date_hierarchy = "last_message_at"
    list_select_related = ("lead", "user")
    actions = ("mark_closed",)
    fields = (
        ("status", "channel"),
        ("name", "telegram_username", "user"),
        ("lead", "locale", "source_page"),
        "summary",
        "context_view",
        ("user_messages", "cost_usd", "last_message_at"),
        "transcript",
    )
    readonly_fields = (
        "channel",
        "name",
        "telegram_username",
        "user",
        "lead",
        "locale",
        "source_page",
        "summary",
        "context_view",
        "user_messages",
        "cost_usd",
        "last_message_at",
        "transcript",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @display(
        description=_("Kanal"),
        ordering="channel",
        label={Conversation.Channel.WEB: "info", Conversation.Channel.TELEGRAM: "info"},
    )
    def show_channel(self, obj: Conversation) -> tuple[str, str]:
        return obj.channel, obj.get_channel_display()

    @display(
        description=_("Holat"),
        ordering="status",
        label={
            Conversation.Status.OPEN: "info",
            Conversation.Status.MANAGER: "danger",
            Conversation.Status.CLOSED: "success",
        },
    )
    def show_status(self, obj: Conversation) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @admin.display(description=_("Mijoz"))
    def contact(self, obj: Conversation) -> str:
        parts = [obj.name, f"@{obj.telegram_username}" if obj.telegram_username else ""]
        if obj.lead is not None:
            parts.append(obj.lead.phone)
        return " · ".join(part for part in parts if part) or "—"

    @admin.display(description=_("Ariza"))
    def lead_link(self, obj: Conversation) -> str:
        if obj.lead_id is None:
            return "—"
        url = reverse("admin:leads_lead_change", args=[obj.lead_id])
        return format_html('<a href="{}" class="underline">#{}</a>', url, obj.lead_id)

    @admin.display(description=_("Xarajat"), ordering="cost_usd")
    def show_cost(self, obj: Conversation) -> str:
        return f"${obj.cost_usd.quantize(Decimal('0.0001'))}"

    @admin.display(description=_("Kontekst"))
    def context_view(self, obj: Conversation) -> str:
        visible = {key: value for key, value in obj.context.items() if key != "lead_calls"}
        return json.dumps(visible, ensure_ascii=False) if visible else "—"

    @admin.display(description=_("Suhbat"))
    def transcript(self, obj: Conversation) -> SafeString | str:
        """Mijoz va AI xabarlari; vosita chaqiruvlari kulrangda."""
        rows = []
        for message in obj.messages.order_by("id"):
            if message.role == Message.Role.TOOL:
                continue
            tools = [
                f"🔧 {block['name']}: {json.dumps(block['input'], ensure_ascii=False)}"
                for block in message.content
                if block.get("type") == "tool_use"
            ]
            who = "👤" if message.role == Message.Role.USER else "🤖"
            rating = f" {message.get_rating_display()}" if message.rating else ""
            rows.append(
                (
                    "background:rgba(127,127,127,.08)" if message.role == Message.Role.USER else "",
                    f"{who} {message.created_at:%d.%m %H:%M}{rating}",
                    message.text or "",
                    "\n".join(tools),
                )
            )
        if not rows:
            return "—"
        return format_html(
            '<div style="display:grid;gap:.5rem;max-width:48rem">{}</div>',
            format_html_join(
                "",
                '<div style="padding:.6rem .8rem;border-radius:.6rem;{}">'
                '<div style="font-size:.75rem;opacity:.7">{}</div>'
                '<div style="white-space:pre-wrap">{}</div>'
                '<div style="white-space:pre-wrap;font-size:.75rem;opacity:.6">{}</div></div>',
                rows,
            ),
        )

    @admin.action(description=_("Yopish (hal qilindi)"))
    def mark_closed(self, request: HttpRequest, queryset: QuerySet[Conversation]) -> None:
        count = queryset.exclude(status=Conversation.Status.CLOSED).update(
            status=Conversation.Status.CLOSED
        )
        self.message_user(request, _("%(count)s ta suhbat yopildi.") % {"count": count})
