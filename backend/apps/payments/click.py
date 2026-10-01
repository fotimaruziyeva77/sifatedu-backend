"""Click SHOP API: to'lov havolasi, imzo va Prepare/Complete mantiqi.

Click ikki marta murojaat qiladi:

* **Prepare** (`action=0`) — buyurtma bormi, summa to'g'rimi;
* **Complete** (`action=1`) — pul yechildi, kursni ochish kerak.

Har ikkisida imzo MD5 bilan tekshiriladi va javob Click hujjatidagi xato kodlari bilan
qaytariladi. Kurs faqat Complete'dan keyin ochiladi.
"""

import hashlib
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core import events
from apps.learning.models import Enrollment

from . import pricing
from .models import Order, PaymentTransaction, Provider

logger = logging.getLogger(__name__)

PAY_URL = "https://my.click.uz/services/pay"

# Click hujjatidagi xato kodlari.
OK = 0
SIGN_FAILED = -1
BAD_AMOUNT = -2
ACTION_NOT_FOUND = -3
ALREADY_PAID = -4
ORDER_NOT_FOUND = -5
TRANSACTION_NOT_FOUND = -6
ORDER_CLOSED = -9

ACTION_PREPARE = "0"
ACTION_COMPLETE = "1"

MESSAGES = {
    OK: "Success",
    SIGN_FAILED: "SIGN CHECK FAILED",
    BAD_AMOUNT: "Incorrect parameter amount",
    ACTION_NOT_FOUND: "Action not found",
    ALREADY_PAID: "Already paid",
    ORDER_NOT_FOUND: "Order does not exist",
    TRANSACTION_NOT_FOUND: "Transaction does not exist",
    ORDER_CLOSED: "Transaction cancelled",
}


class ClickError(Exception):
    """Click'ga qaytariladigan xato kodi."""

    def __init__(self, code: int) -> None:
        super().__init__(MESSAGES.get(code, "Error"))
        self.code = code


@dataclass(frozen=True)
class Callback:
    """Click yuborgan maydonlar (kerakli qismi)."""

    click_trans_id: str
    service_id: str
    merchant_trans_id: str
    merchant_prepare_id: str
    amount: str
    action: str
    error: int
    sign_time: str
    sign_string: str
    paydoc_id: str

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "Callback":
        def text(key: str) -> str:
            value = data.get(key, "")
            return str(value) if value is not None else ""

        try:
            error = int(text("error") or 0)
        except ValueError:
            error = 0
        return cls(
            click_trans_id=text("click_trans_id"),
            service_id=text("service_id"),
            merchant_trans_id=text("merchant_trans_id"),
            merchant_prepare_id=text("merchant_prepare_id"),
            amount=text("amount"),
            action=text("action"),
            error=error,
            sign_time=text("sign_time"),
            sign_string=text("sign_string"),
            paydoc_id=text("click_paydoc_id"),
        )


def configured() -> bool:
    return bool(settings.CLICK_SERVICE_ID and settings.CLICK_SECRET_KEY)


def pay_url(order: Order, locale: str) -> str:
    """O'quvchi yuboriladigan Click sahifasi. To'lovdan keyin u o'z tilidagi sahifaga qaytadi."""
    language = locale if locale in dict(settings.LANGUAGES) else settings.LANGUAGE_CODE
    query = urlencode(
        {
            "service_id": settings.CLICK_SERVICE_ID,
            "merchant_id": settings.CLICK_MERCHANT_ID,
            "amount": order.amount,
            "transaction_param": order.pk,
            "return_url": f"{settings.APP_URL}/{language}/payment/result?order={order.pk}",
        }
    )
    return f"{PAY_URL}?{query}"


def _signature(parts: list[str]) -> str:
    return hashlib.md5("".join(parts).encode()).hexdigest()  # noqa: S324 - Click MD5 talab qiladi


def check_sign(callback: Callback) -> None:
    """Imzo Click hujjatidagi tartibda yig'iladi.

    Complete'da `merchant_prepare_id` ham qatnashadi — shuning uchun ikki variant.
    """
    parts = [
        callback.click_trans_id,
        callback.service_id,
        settings.CLICK_SECRET_KEY,
        callback.merchant_trans_id,
    ]
    if callback.action == ACTION_COMPLETE:
        parts.append(callback.merchant_prepare_id)
    parts += [callback.amount, callback.action, callback.sign_time]

    expected = _signature(parts)
    # `compare_digest` emas: qiymat hex matn, uzunligi doim bir xil va sir emas.
    if not callback.sign_string or callback.sign_string.lower() != expected:
        raise ClickError(SIGN_FAILED)


def _order_for(callback: Callback) -> Order:
    try:
        order_id = int(callback.merchant_trans_id)
    except (TypeError, ValueError) as exc:
        raise ClickError(ORDER_NOT_FOUND) from exc
    order = Order.objects.select_for_update().filter(pk=order_id).first()
    if order is None:
        raise ClickError(ORDER_NOT_FOUND)
    return order


def _check_amount(order: Order, amount: str) -> None:
    """Click summani "1000.00" ko'rinishida yuboradi."""
    try:
        value = Decimal(amount)
    except (InvalidOperation, TypeError) as exc:
        raise ClickError(BAD_AMOUNT) from exc
    if value != Decimal(order.amount):
        raise ClickError(BAD_AMOUNT)


@transaction.atomic
def prepare(callback: Callback) -> dict[str, Any]:
    """Buyurtmani tekshiradi va tranzaksiyani band qiladi."""
    check_sign(callback)
    order = _order_for(callback)
    _check_amount(order, callback.amount)

    if order.status == Order.Status.PAID:
        raise ClickError(ALREADY_PAID)
    if not order.is_open:
        raise ClickError(ORDER_CLOSED)
    if callback.error < 0:
        raise ClickError(ORDER_CLOSED)

    try:
        payment, _created = PaymentTransaction.objects.get_or_create(
            provider=Provider.CLICK,
            provider_trans_id=callback.click_trans_id,
            defaults={
                "order": order,
                "amount": order.amount,
                "paydoc_id": callback.paydoc_id,
            },
        )
    except IntegrityError as exc:  # Bir vaqtda kelgan takroriy so'rov.
        raise ClickError(ALREADY_PAID) from exc

    if payment.order_id != order.pk:
        raise ClickError(TRANSACTION_NOT_FOUND)
    if payment.status == PaymentTransaction.Status.CONFIRMED:
        raise ClickError(ALREADY_PAID)
    if payment.status == PaymentTransaction.Status.CANCELLED:
        raise ClickError(ORDER_CLOSED)

    return {
        "click_trans_id": callback.click_trans_id,
        "merchant_trans_id": str(order.pk),
        "merchant_prepare_id": payment.pk,
        "error": OK,
        "error_note": MESSAGES[OK],
    }


def complete(callback: Callback) -> dict[str, Any]:
    """Pul yechilgandan keyin kursni ochadi.

    Click xato bilan kelsa, tranzaksiya bekor qilinadi — bu yozuv saqlanishi kerak,
    shuning uchun xato tranzaksiya yopilgandan keyin ko'tariladi.
    """
    with transaction.atomic():
        result, cancelled = _complete(callback)
    if cancelled:
        raise ClickError(ORDER_CLOSED)
    return result


def _complete(callback: Callback) -> tuple[dict[str, Any], bool]:
    check_sign(callback)
    order = _order_for(callback)
    _check_amount(order, callback.amount)

    payment = (
        PaymentTransaction.objects.select_for_update()
        .filter(provider=Provider.CLICK, provider_trans_id=callback.click_trans_id)
        .first()
    )
    if payment is None or str(payment.pk) != callback.merchant_prepare_id:
        raise ClickError(TRANSACTION_NOT_FOUND)
    if payment.order_id != order.pk:
        raise ClickError(TRANSACTION_NOT_FOUND)
    if payment.status == PaymentTransaction.Status.CANCELLED:
        raise ClickError(ORDER_CLOSED)
    if payment.status == PaymentTransaction.Status.CONFIRMED:
        # Click so'rovni takrorlagan: holat o'zgarmaydi, javob o'sha-o'sha.
        raise ClickError(ALREADY_PAID)

    # Click o'zi xato bilan keldi: tranzaksiya bekor qilinadi, kurs ochilmaydi.
    if callback.error < 0:
        payment.status = PaymentTransaction.Status.CANCELLED
        payment.cancelled_at = timezone.now()
        payment.save(update_fields=["status", "cancelled_at", "updated_at"])
        return {}, True

    if order.status == Order.Status.PAID:
        raise ClickError(ALREADY_PAID)
    if not order.is_open:
        raise ClickError(ORDER_CLOSED)

    now = timezone.now()
    payment.status = PaymentTransaction.Status.CONFIRMED
    payment.confirmed_at = now
    payment.paydoc_id = callback.paydoc_id or payment.paydoc_id
    payment.save(update_fields=["status", "confirmed_at", "paydoc_id", "updated_at"])

    order.status = Order.Status.PAID
    order.paid_at = now
    order.save(update_fields=["status", "paid_at", "updated_at"])

    grant_access(order)
    events.order_paid.send(sender=Order, order=order)
    transaction.on_commit(lambda: _after_payment(payment.pk))

    return {
        "click_trans_id": callback.click_trans_id,
        "merchant_trans_id": str(order.pk),
        "merchant_confirm_id": payment.pk,
        "error": OK,
        "error_note": MESSAGES[OK],
    }, False


def grant_access(order: Order) -> Enrollment:
    """Kursni ochadi. Offlayn uchun muddat to'langan oylarga qarab uzayadi."""
    is_offline = order.study_format == Order.Format.OFFLINE
    expires_at = pricing.offline_expiry(order) if is_offline else None

    enrollment, created = Enrollment.objects.get_or_create(
        user=order.user,
        course=order.course,
        defaults={
            "source": Enrollment.Source.PAYMENT,
            "study_format": (Enrollment.Format.OFFLINE if is_offline else Enrollment.Format.ONLINE),
            "expires_at": expires_at,
        },
    )
    if not created:
        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.source = Enrollment.Source.PAYMENT
        if is_offline:
            enrollment.study_format = Enrollment.Format.OFFLINE
            enrollment.expires_at = expires_at
        else:
            # Onlayn to'lov muddatsiz kirish beradi.
            enrollment.study_format = Enrollment.Format.ONLINE
            enrollment.expires_at = None
        enrollment.save(
            update_fields=["status", "source", "study_format", "expires_at", "updated_at"]
        )
    return enrollment


def _after_payment(payment_id: int) -> None:
    """Fiskal chek va xabar — tranzaksiya yopilgandan keyin."""
    from .tasks import finish_payment

    finish_payment.delay(payment_id)
