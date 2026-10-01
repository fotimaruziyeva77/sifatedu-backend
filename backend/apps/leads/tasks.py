import logging
from html import escape

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.notifications import telegram

from .models import Lead

logger = logging.getLogger(__name__)


def build_message(lead: Lead) -> str:
    utm = " / ".join(
        value for value in (lead.utm_source, lead.utm_medium, lead.utm_campaign) if value
    )
    title = (
        "Yangi ariza"
        if lead.source == Lead.Source.FORM
        else f"Yangi ariza · {lead.get_source_display()}"
    )
    lines = [
        f"<b>{escape(title)}</b>",
        f"Ism: {escape(lead.name)}",
        f"Telefon: {escape(lead.phone)}",
        f"Kurs: {escape(str(lead.course)) if lead.course else '—'}",
    ]
    if lead.comment:
        lines.append(f"Izoh: {escape(lead.comment)}")
    if lead.source_page:
        lines.append(f"Sahifa: {escape(lead.source_page)}")
    if utm:
        lines.append(f"UTM: {escape(utm)}")
    return "\n".join(lines)


@shared_task(
    autoretry_for=(OSError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def notify_new_lead(lead_id: int) -> None:
    lead = Lead.objects.select_related("course").filter(pk=lead_id).first()
    if lead is None or lead.telegram_sent_at is not None:
        return
    try:
        telegram.send_message(settings.TELEGRAM_LEADS_CHAT_ID, build_message(lead))
    except telegram.TelegramNotConfiguredError:
        logger.info("Telegram sozlanmagan: ariza #%s faqat admin panelda", lead_id)
        return
    Lead.objects.filter(pk=lead_id).update(telegram_sent_at=timezone.now())
