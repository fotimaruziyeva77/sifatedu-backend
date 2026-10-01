import csv

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Lead

CSV_COLUMNS = (
    ("created_at", "Sana"),
    ("name", "Ism"),
    ("phone", "Telefon"),
    ("course", "Kurs"),
    ("status", "Holat"),
    ("comment", "Izoh"),
    ("manager_note", "Menejer izohi"),
    ("submissions", "Murojaatlar"),
    ("source", "Manba"),
    ("utm_source", "utm_source"),
    ("utm_medium", "utm_medium"),
    ("utm_campaign", "utm_campaign"),
    ("source_page", "Sahifa"),
)


@admin.register(Lead)
class LeadAdmin(ModelAdmin):
    list_display = (
        "name",
        "phone",
        "course",
        "show_status",
        "show_source",
        "submissions",
        "utm_source",
        "created_at",
    )
    list_filter = ("status", "source", "course", "locale", "utm_source", "created_at")
    list_filter_submit = True
    search_fields = ("name", "phone", "comment")
    date_hierarchy = "created_at"
    list_select_related = ("course",)
    actions = ("mark_contacted", "export_csv")
    warn_unsaved_form = True
    readonly_fields = (
        "source",
        "ai_conversations",
        "submissions",
        "locale",
        "source_page",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ip",
        "user_agent",
        "telegram_sent_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {"fields": ("name", "phone", "course", "comment")}),
        (_("Ishlov berish"), {"fields": ("status", "manager_note")}),
        (
            _("Manba"),
            {
                "classes": ("collapse",),
                "fields": (
                    ("source", "ai_conversations"),
                    "source_page",
                    ("utm_source", "utm_medium", "utm_campaign"),
                    ("utm_term", "utm_content"),
                    "locale",
                ),
            },
        ),
        (
            _("Texnik ma'lumotlar"),
            {
                "classes": ("collapse",),
                "fields": (
                    "submissions",
                    "ip",
                    "user_agent",
                    "telegram_sent_at",
                    ("created_at", "updated_at"),
                ),
            },
        ),
    )

    @display(
        description=_("Holat"),
        ordering="status",
        label={
            Lead.Status.NEW: "danger",
            Lead.Status.CONTACTED: "warning",
            Lead.Status.CONVERTED: "success",
            Lead.Status.REJECTED: "info",
        },
    )
    def show_status(self, obj: Lead) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(
        description=_("Manba"),
        ordering="source",
        label={
            Lead.Source.FORM: "info",
            Lead.Source.AI_WEB: "success",
            Lead.Source.AI_TELEGRAM: "success",
        },
    )
    def show_source(self, obj: Lead) -> tuple[str, str]:
        return obj.source, obj.get_source_display()

    @admin.display(description=_("AI suhbat"))
    def ai_conversations(self, obj: Lead) -> str:
        """AI suhbatdan kelgan ariza: transkriptga havola (menejer o'qib, qo'ng'iroq qiladi)."""
        links = [
            (reverse("admin:assistant_conversation_change", args=[pk]), f"#{pk}")
            for pk in obj.conversations.values_list("pk", flat=True)
        ]
        if not links:
            return "—"
        return format_html_join(", ", '<a href="{}" class="underline">{}</a>', links)

    @admin.action(description=_("Bog'lanildi deb belgilash"))
    def mark_contacted(self, request: HttpRequest, queryset: QuerySet[Lead]) -> None:
        # update() signal yubormaydi: har biri saqlanadi, audit log'da kim o'zgartirgani qoladi.
        leads = list(queryset.filter(status=Lead.Status.NEW))
        for lead in leads:
            lead.status = Lead.Status.CONTACTED
            lead.save(update_fields=["status", "updated_at"])
        self.message_user(request, _("%(count)s ta ariza yangilandi.") % {"count": len(leads)})

    @admin.action(description=_("CSV'ga eksport qilish"))
    def export_csv(self, request: HttpRequest, queryset: QuerySet[Lead]) -> HttpResponse:
        filename = f"arizalar-{timezone.localdate():%Y-%m-%d}.csv"
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("﻿")  # Excel UTF-8'ni to'g'ri ochishi uchun BOM
        writer = csv.writer(response)
        writer.writerow([title for _field, title in CSV_COLUMNS])
        for lead in queryset.select_related("course"):
            writer.writerow(
                csv_cell(value)
                for value in [
                    timezone.localtime(lead.created_at).strftime("%Y-%m-%d %H:%M"),
                    lead.name,
                    lead.phone,
                    lead.course or "",
                    lead.get_status_display(),
                    lead.comment,
                    lead.manager_note,
                    lead.submissions,
                    lead.get_source_display(),
                    lead.utm_source,
                    lead.utm_medium,
                    lead.utm_campaign,
                    lead.source_page,
                ]
            )
        return response


# Excel "=", "+", "-", "@" bilan boshlangan katakni formula deb bajaradi. Ism va izohlarni
# saytdan istalgan odam yuboradi, shuning uchun bunday qiymatlar matn sifatida belgilanadi.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_cell(value: object) -> str:
    text = str(value)
    return f"'{text}" if text.startswith(FORMULA_PREFIXES) else text
