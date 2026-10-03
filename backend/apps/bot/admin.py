"""Admin: bot foydalanuvchilari (faqat ko'rish) va majburiy obuna kanallari."""

from typing import Any

from django.contrib import admin
from django.db.models import CharField, Exists, OuterRef, QuerySet, Subquery
from django.db.models.functions import Cast
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.live.admin import HttpsLinks
from apps.users.models import SocialAccount

from . import subscription
from .models import BotChat, RequiredChannel


def telegram_accounts() -> QuerySet[SocialAccount]:
    """Shu chatga ulangan akkaunt (Telegram ID = chat ID)."""
    return SocialAccount.objects.filter(
        provider=SocialAccount.Provider.TELEGRAM,
        uid=Cast(OuterRef("chat_id"), output_field=CharField()),
    )


class RegisteredFilter(admin.SimpleListFilter):
    title = _("ro'yxatdan o'tgan")
    parameter_name = "registered"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        return [("yes", str(_("Ha"))), ("no", str(_("Yo'q")))]

    def queryset(self, request: HttpRequest, queryset: QuerySet[BotChat]) -> QuerySet[BotChat]:
        if self.value() == "yes":
            return queryset.filter(Exists(telegram_accounts()))
        if self.value() == "no":
            return queryset.exclude(Exists(telegram_accounts()))
        return queryset


@admin.register(BotChat)
class BotChatAdmin(ModelAdmin):
    """Botga /start bosganlar: yangiliklar shu ro'yxatga boradi. Faqat ko'rish."""

    list_display = (
        "__str__",
        "show_user",
        "language",
        "source",
        "news",
        "show_blocked",
        "last_seen_at",
        "created_at",
    )
    list_filter = (RegisteredFilter, "source", "language", "news")
    search_fields = ("chat_id", "first_name", "username")
    date_hierarchy = "created_at"
    fields = (
        "chat_id",
        "first_name",
        "username",
        "show_user",
        "language",
        "news",
        "blocked_at",
        "referral_code",
        "source",
        "last_seen_at",
        "created_at",
    )
    readonly_fields = fields

    def get_queryset(self, request: HttpRequest) -> QuerySet[BotChat]:
        accounts = telegram_accounts()
        return (
            super()
            .get_queryset(request)
            .annotate(
                account_user=Subquery(accounts.values("user_id")[:1]),
                account_phone=Subquery(accounts.values("user__phone")[:1]),
            )
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @admin.display(description=_("Akkaunt"))
    def show_user(self, obj: BotChat) -> str:
        user_id = getattr(obj, "account_user", None)
        if not user_id:
            return str(_("Ro'yxatdan o'tmagan"))
        url = reverse("admin:users_user_change", args=[user_id])
        return format_html('<a href="{}">{}</a>', url, getattr(obj, "account_phone", user_id))

    @display(description=_("Botni bloklagan"), boolean=True)
    def show_blocked(self, obj: BotChat) -> bool:
        return obj.blocked_at is not None


@admin.register(RequiredChannel)
class RequiredChannelAdmin(HttpsLinks, ModelAdmin):
    """Botdan foydalanish uchun obuna bo'linadigan kanallar. Bot kanalda administrator bo'lsin."""

    list_display = ("title", "chat", "url", "is_active", "order", "show_problem")
    list_editable = ("is_active", "order")
    search_fields = ("title", "chat")
    fields = ("title", "chat", "url", "is_active", "order")

    def get_form(
        self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any
    ) -> Any:
        form = super().get_form(request, obj, change=change, **kwargs)
        field = form.base_fields.get("chat")
        known = subscription.admin_channels()
        # Yopiq kanal ID sini bilish qiyin: bot administrator qilingan kanallar shu yerda.
        if field is not None and known:
            listed = "; ".join(f"«{title}» — {chat_id}" for chat_id, title in known)
            field.help_text = format_html(
                "{}<br>{}: <b>{}</b>",
                field.help_text,
                _("Bot administrator bo'lgan kanallar"),
                listed,
            )
        return form

    @admin.display(description=_("Tekshiruv"))
    def show_problem(self, obj: RequiredChannel) -> str:
        note = subscription.problem(obj.pk)
        if note:
            return str(_("Bot a'zolikni tekshira olmayapti: %(note)s") % {"note": note})
        return "—"
