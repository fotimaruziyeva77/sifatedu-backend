"""To'lovdan keyingi ishlar va to'lanmagan buyurtmalarni yopish."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import override as language

from apps.notifications.alerts import alert
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import locale_of, text

from . import fiscal
from .models import ORDER_TTL_MINUTES, Order, PaymentTransaction

logger = logging.getLogger(__name__)


@shared_task
def finish_payment(payment_id: int) -> str:
    """Fiskal chek va o'quvchiga xabar. To'lovning o'zi allaqachon yozilgan."""
    payment = (
        PaymentTransaction.objects.select_related("order", "order__user", "order__course")
        .filter(pk=payment_id)
        .first()
    )
    if payment is None:
        return "yo'q"

    if fiscal.missing_mxik(payment):
        logger.warning("MXIK kodi yo'q: kurs=%s", payment.order.course_id)

    try:
        url = fiscal.submit(payment)
    except Exception:  # Chek yuborilmasa ham kurs ochiq qolishi kerak.
        logger.exception("Fiskal chek yuborilmadi: %s", payment.provider_trans_id)
        alert("fiscal:failed", f"Fiskal chek yuborilmadi: tranzaksiya {payment.provider_trans_id}")
        url = ""
    if url and url != payment.fiscal_receipt_url:
        payment.fiscal_receipt_url = url
        payment.save(update_fields=["fiscal_receipt_url", "updated_at"])

    _notify(payment)
    return "ok"


def _notify(payment: PaymentTransaction) -> None:
    """Kabinetga va Telegram'ga; Telegram bo'lmasa — SMS (oldingidek)."""
    order = payment.order
    user = order.user
    locale = locale_of(user.locale)
    with language(locale):
        course = str(order.course.title)
        sms = gettext("To'lov qabul qilindi. «%(course)s» kursi ochildi.") % {"course": course}
        if payment.fiscal_receipt_url:
            sms += gettext(" Chek: %(url)s") % {"url": payment.fiscal_receipt_url}
    body = text(locale, "payment_body", course=course)
    if payment.fiscal_receipt_url:
        body += "\n" + text(locale, "receipt", url=payment.fiscal_receipt_url)
    notify(
        user,
        Notification.Kind.PAYMENT,
        title=text(locale, "payment_title"),
        body=body,
        link=f"/dashboard/courses/{order.course.slug}",
        sms_text=sms,
        dedupe_key=f"payment:{payment.pk}",
    )


@shared_task
def expire_orders() -> str:
    """To'lanmagan buyurtma 30 daqiqadan keyin yopiladi (TZ talabi)."""
    deadline = timezone.now() - timedelta(minutes=ORDER_TTL_MINUTES)
    count = Order.objects.filter(status=Order.Status.NEW, created_at__lt=deadline).update(
        status=Order.Status.EXPIRED, updated_at=timezone.now()
    )
    if count:
        logger.info("Muddati o'tgan buyurtmalar yopildi: %s", count)
    return f"{count}"
