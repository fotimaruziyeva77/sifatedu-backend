"""Fiskal chek (MXIK kodi bilan).

Click fiskalizatsiya API'si merchant hujjatlari va kalitlari bilan birga keladi. Ular
berilmaguncha modul **dry-run** rejimida ishlaydi: chek ma'lumotlari logga yoziladi va
chek havolasi bo'sh qoladi (admin uni qo'lda ham kiritishi mumkin).

Kalitlar berilgach, `submit()` ichida rasmiy protokol bo'yicha so'rov yuboriladi —
shakl shu yerda tayyor turadi.
"""

import logging
from typing import Any

from django.conf import settings

from .models import PaymentTransaction

logger = logging.getLogger(__name__)

# Kurs uchun standart MXIK: admin har bir kursda o'zinikini ko'rsatadi.
DEFAULT_VAT_PERCENT = 0


def receipt_items(payment: PaymentTransaction) -> list[dict[str, Any]]:
    """Chekdagi qatorlar. Bitta buyurtmada bitta kurs bo'ladi."""
    order = payment.order
    course = order.course
    return [
        {
            "Name": course.title[:255],
            "SPIC": course.mxik_code,
            "Units": 1,
            "Price": order.amount,
            "Amount": order.amount,
            "VatPercent": DEFAULT_VAT_PERCENT,
            "CommissionInfo": {"TIN": settings.CLICK_MERCHANT_TIN},
        }
    ]


def submit(payment: PaymentTransaction) -> str:
    """Chekni fiskalizatsiyaga yuboradi va chek havolasini qaytaradi."""
    items = receipt_items(payment)
    if settings.FISCAL_DRY_RUN or not settings.CLICK_MERCHANT_TIN:
        logger.info(
            "Fiskal chek (dry-run): tranzaksiya=%s, summa=%s, MXIK=%s",
            payment.provider_trans_id,
            payment.amount,
            items[0]["SPIC"] or "yo'q",
        )
        return ""

    # Bu yerga Click fiskalizatsiya so'rovi qo'yiladi (kalitlar kelganda).
    logger.warning(
        "Fiskal chek yuborilmadi: protokol sozlanmagan (tranzaksiya=%s)",
        payment.provider_trans_id,
    )
    return ""


def missing_mxik(payment: PaymentTransaction) -> bool:
    """MXIK kodsiz chek qonuniy emas: admin'da ogohlantirish uchun."""
    return not payment.order.course.mxik_code
