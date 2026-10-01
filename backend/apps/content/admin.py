from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.contrib.forms.widgets import WysiwygWidget

from apps.core.admin_utils import TranslatedModelAdmin, language_tabs

from .models import (
    Advantage,
    Concern,
    FAQItem,
    HowStep,
    LegalPage,
    SiteSettings,
    Testimonial,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(TranslatedModelAdmin):
    fieldsets = [
        (_("Kontaktlar"), {"fields": ["phone", "email"]}),
        (
            _("Ijtimoiy tarmoqlar"),
            {"fields": ["telegram_url", "instagram_url", "youtube_url", "facebook_url"]},
        ),
        (
            _("Bo'limlar"),
            {"fields": ["show_stats", "show_instructors", "show_testimonials"]},
        ),
        (_("Biz kimmiz: video"), {"fields": ["promo_video", "promo_poster"]}),
        *language_tabs(["hero_title", "hero_subtitle", "about_text", "address", "working_hours"]),
    ]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj: SiteSettings | None = None) -> bool:
        return False

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, object] | None = None
    ) -> HttpResponse:
        # Yagona yozuv: ro'yxat o'rniga darhol tahrirlash sahifasi ochiladi (ruxsat bo'lsa).
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        obj = SiteSettings.load()
        return redirect(reverse("admin:content_sitesettings_change", args=[obj.pk]))


class OrderedContentAdmin(TranslatedModelAdmin):
    list_filter = ("is_published",)
    ordering_field = "order"
    hide_ordering_field = True


@admin.register(Advantage)
class AdvantageAdmin(OrderedContentAdmin):
    list_display = ("title", "icon", "is_published")
    fieldsets = [(None, {"fields": ["icon", "is_published"]}), *language_tabs(["title", "text"])]


@admin.register(Concern)
class ConcernAdmin(OrderedContentAdmin):
    list_display = ("problem", "answer", "is_published")
    search_fields = ("problem",)
    fieldsets = [(None, {"fields": ["is_published"]}), *language_tabs(["problem", "answer"])]


@admin.register(HowStep)
class HowStepAdmin(OrderedContentAdmin):
    list_display = ("title", "is_published")
    fieldsets = [(None, {"fields": ["is_published"]}), *language_tabs(["title", "text"])]


@admin.register(FAQItem)
class FAQItemAdmin(OrderedContentAdmin):
    list_display = ("question", "is_published")
    search_fields = ("question",)
    fieldsets = [
        (None, {"fields": ["is_published"]}),
        *language_tabs(["question", "answer"]),
    ]


@admin.register(Testimonial)
class TestimonialAdmin(OrderedContentAdmin):
    list_display = ("author_name", "author_role", "is_published")
    search_fields = ("author_name",)
    fieldsets = [
        (None, {"fields": ["author_name", "avatar", "is_published"]}),
        *language_tabs(["author_role", "text"]),
    ]


@admin.register(LegalPage)
class LegalPageAdmin(TranslatedModelAdmin):
    list_display = ("title", "slug", "version", "updated_at")
    formfield_overrides = {models.TextField: {"widget": WysiwygWidget}}
    fieldsets = [(None, {"fields": ["slug", "version"]}), *language_tabs(["title", "body"])]
