"""Unfold admin uchun callback'lar."""

from django.conf import settings
from django.http import HttpRequest


def environment_callback(request: HttpRequest) -> list[str] | None:
    if settings.DEBUG:
        return ["Development", "warning"]
    return None


def new_leads_badge(request: HttpRequest) -> str | None:
    """Menyuda ko'rib chiqilmagan arizalar soni."""
    from apps.leads.models import Lead

    count = Lead.objects.filter(status=Lead.Status.NEW).count()
    return str(count) if count else None


def manager_needed_badge(request: HttpRequest) -> str | None:
    """AI suhbatlardan menejer aralashuvini kutayotganlari."""
    from apps.assistant.models import Conversation

    count = Conversation.objects.filter(status=Conversation.Status.MANAGER).count()
    return str(count) if count else None
