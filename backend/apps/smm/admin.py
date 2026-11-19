from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from apps.core.storage import public_storage

from . import services, tasks
from .models import Post, SmmSettings


@admin.register(SmmSettings)
class SmmSettingsAdmin(admin.ModelAdmin):
    fields = ("enabled", "auto_publish", "channel", "publish_hour", "about")
    actions = ("plan_next_week",)

    @admin.action(description=_("Keyingi hafta rejasini tuzish"), permissions=["change"])
    def plan_next_week(self, request: HttpRequest, queryset: QuerySet[SmmSettings]) -> None:
        try:
            created = services.plan_week()
        except services.ai.AiError as exc:
            self.message_user(request, str(exc), messages.ERROR)
            return
        if created:
            self.message_user(
                request, format_html("Reja tuzildi: {} ta", len(created)), messages.SUCCESS
            )
        else:
            self.message_user(request, "Keyingi hafta allaqachon rejalangan.", messages.WARNING)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not SmmSettings.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("publish_at", "kind", "formula", "topic", "status", "cost_usd")
    list_filter = ("status", "kind", "formula")
    search_fields = ("topic", "caption")
    date_hierarchy = "publish_at"
    readonly_fields = (
        "preview",
        "status",
        "attempts",
        "cost_usd",
        "error",
        "decided_by",
        "published_at",
        "content",
    )
    fields = (
        "publish_at",
        "kind",
        "formula",
        "topic",
        "angle",
        "preview",
        "caption",
        "caption_tg",
        "status",
        "attempts",
        "cost_usd",
        "decided_by",
        "published_at",
        "error",
        "content",
    )
    actions = ("prepare_now", "publish_now")

    @admin.display(description=_("rasmlar"))
    def preview(self, obj: Post) -> str:
        storage = public_storage()
        return (
            format_html_join(
                "",
                '<img src="{}" style="width:180px;margin:0 8px 8px 0;border-radius:8px">',
                ((storage.url(name),) for name in obj.images or []),
            )
            or "—"
        )

    @admin.action(description=_("Hozir tayyorlash va tasdiqqa yuborish"), permissions=["change"])
    def prepare_now(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        count = 0
        # Kanalga qisman chiqqan post qayta yasalmaydi (ikkinchi marta chiqib ketmasin).
        for post in queryset.filter(
            status__in=[Post.Status.PLANNED, Post.Status.FAILED], channel_messages=[]
        ):
            Post.objects.filter(pk=post.pk).update(status=Post.Status.PLANNED, error="")
            tasks.prepare.delay(post.pk)
            count += 1
        self.message_user(request, format_html("Tayyorlanmoqda: {}", count), messages.SUCCESS)

    @admin.action(
        description=_("Hozir kanalga chiqarish (tasdiqlanganlar)"), permissions=["change"]
    )
    def publish_now(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        count = 0
        for post in queryset.filter(status=Post.Status.APPROVED).exclude(kind=Post.Kind.SCRIPT):
            tasks.publish.delay(post.pk)
            count += 1
        self.message_user(request, format_html("Navbatga qo'yildi: {}", count), messages.SUCCESS)
