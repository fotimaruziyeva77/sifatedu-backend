"""Arizani qabul qilish: takroriy murojaatlarni birlashtirish va Telegram'ga yuborish."""

from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Course

from .models import Lead
from .tasks import notify_new_lead

DUPLICATE_WINDOW = timedelta(hours=24)


@dataclass
class LeadInput:
    name: str
    phone: str
    course: Course | None = None
    comment: str = ""
    locale: str = "uz"
    source_page: str = ""
    utm: dict[str, str] = field(default_factory=dict)
    ip: str | None = None
    user_agent: str = ""
    source: str = Lead.Source.FORM


def submit_lead(data: LeadInput) -> tuple[Lead, bool]:
    """Arizani saqlaydi. Bitta raqamdan 24 soat ichida kelgan yangi ariza bo'lsa, unga qo'shadi.

    Qaytaradi: (ariza, yangi yaratildimi).
    """
    with transaction.atomic():
        existing = (
            Lead.objects.select_for_update()
            .filter(
                phone=data.phone,
                status=Lead.Status.NEW,
                created_at__gte=timezone.now() - DUPLICATE_WINDOW,
            )
            .order_by("-created_at")
            .first()
        )
        if existing is not None:
            existing.name = data.name
            existing.submissions += 1
            if data.course is not None:
                existing.course = data.course
            if data.comment:
                existing.comment = "\n---\n".join(filter(None, [existing.comment, data.comment]))
            existing.save()
            return existing, False

        lead = Lead.objects.create(
            name=data.name,
            phone=data.phone,
            course=data.course,
            comment=data.comment,
            source=data.source,
            locale=data.locale,
            source_page=data.source_page,
            ip=data.ip,
            user_agent=data.user_agent,
            **{key: value for key, value in data.utm.items() if key.startswith("utm_")},
        )
        transaction.on_commit(lambda: notify_new_lead.delay(lead.pk))
        return lead, True
