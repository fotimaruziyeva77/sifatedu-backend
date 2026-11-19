from typing import Any

from django import forms
from django.contrib import admin, messages
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from apps.core.storage import public_storage

from . import services, tasks
from .models import Post, SmmSettings


class SmmSettingsForm(forms.ModelForm):
    # Token hech qachon sahifaga qaytarilmaydi: bo'sh qoldirilsa, eskisi saqlanadi.
    new_ig_token = forms.CharField(
        label=_("Instagram tokeni"),
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "off"}),
        help_text=_(
            "Meta → ilova → Instagram → API setup with Instagram business login → Generate token. "
            "Kiritgach, saqlang va «Instagram'ni tekshirish» amalini bajaring."
        ),
    )

    class Meta:
        model = SmmSettings
        fields = ("enabled", "auto_publish", "channel", "publish_hour", "about", "instagram")

    def save(self, commit: bool = True) -> SmmSettings:
        row = super().save(commit=False)
        token = self.cleaned_data.get("new_ig_token", "").strip()
        if token:
            row.ig_token = token
            row.ig_user_id = row.ig_username = ""
            row.ig_token_refreshed_at = None
        if commit:
            row.save()
        return row


@admin.register(SmmSettings)
class SmmSettingsAdmin(admin.ModelAdmin):
    form = SmmSettingsForm
    fieldsets = (
        (None, {"fields": ("enabled", "auto_publish", "channel", "publish_hour", "about")}),
        (
            _("Instagram"),
            {
                "fields": (
                    "instagram",
                    "new_ig_token",
                    "ig_username",
                    "ig_user_id",
                    "ig_token_refreshed_at",
                    "ig_error",
                )
            },
        ),
    )
    readonly_fields = ("ig_username", "ig_user_id", "ig_token_refreshed_at", "ig_error")
    actions = ("plan_next_week", "check_instagram")

    @admin.action(description=_("Instagram'ni tekshirish"), permissions=["change"])
    def check_instagram(self, request: HttpRequest, queryset: QuerySet[SmmSettings]) -> None:
        try:
            username = services.connect_instagram()
        except services.instagram.InstagramError as exc:
            self.message_user(request, str(exc), messages.ERROR)
            return
        self.message_user(request, format_html("Instagram ulandi: @{}", username), messages.SUCCESS)

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
        "ig_permalink",
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
        "ig_permalink",
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
        # Xato bo'lganlari ham: qaysi joyga chiqib bo'lgan bo'lsa, o'sha qayta yuborilmaydi.
        # Xato bo'lganlaridan faqat tasdiqlangani (yoki qisman chiqqani) — qayta yasashga
        # yuborilgan, tasdiqlanmagan variant chiqib ketmasin.
        failed_ok = Q(decided_by__isnull=False) | ~Q(channel_messages=[]) | ~Q(ig_container_id="")
        ready = queryset.filter(
            Q(status=Post.Status.APPROVED) | (Q(status=Post.Status.FAILED) & failed_ok)
        )
        for post in ready.exclude(kind=Post.Kind.SCRIPT).exclude(images=[]):
            Post.objects.filter(pk=post.pk).update(status=Post.Status.APPROVED)
            tasks.publish.delay(post.pk)
            count += 1
        self.message_user(request, format_html("Navbatga qo'yildi: {}", count), messages.SUCCESS)
