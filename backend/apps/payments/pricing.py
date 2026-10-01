"""Summa faqat shu yerda hisoblanadi: clientdan kelgan summaga hech qachon ishonilmaydi."""

from datetime import date, datetime, timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.catalog.models import Course
from apps.learning import access

from .models import MAX_MONTHS, Order


class PriceError(serializers.ValidationError):
    pass


def amount_for(course: Course, study_format: str, months: int) -> int:
    """Buyurtma summasi. Kurs shu shaklda sotilmasa yoki narx qo'yilmagan bo'lsa — xato."""
    if course.is_free:
        raise PriceError({"detail": _("Bu kurs bepul, uni sotib olish shart emas.")})

    if study_format == Order.Format.ONLINE:
        if course.study_format == Course.Format.OFFLINE:
            raise PriceError({"study_format": [_("Bu kurs faqat offlayn o'qitiladi.")]})
        price = course.price_online
        months = 1
    else:
        if course.study_format == Course.Format.ONLINE:
            raise PriceError({"study_format": [_("Bu kurs faqat onlayn o'qitiladi.")]})
        price = course.price_offline_monthly

    if price <= 0:
        raise PriceError({"detail": _("Bu kursning narxi hali belgilanmagan.")})
    if not 1 <= months <= MAX_MONTHS:
        raise PriceError({"months": [_("Oylar soni 1 dan 12 gacha bo'lishi kerak.")]})
    return price * months


def check_can_buy(user: object, course: Course, study_format: str) -> None:
    """Allaqachon ochiq kursni qayta sotib olishdan to'sadi.

    Offlayn abonementni uzaytirish mumkin, shuning uchun faqat onlayn tekshiriladi.
    """
    if course.status != Course.Status.PUBLISHED:
        raise PriceError({"detail": _("Bu kurs sotuvda emas.")})
    if study_format != Order.Format.ONLINE:
        return
    enrollment = access.open_enrollment(user, course)
    if enrollment is not None and enrollment.expires_at is None:
        raise PriceError({"detail": _("Bu kurs sizda allaqachon ochiq.")})


def add_months(start: date, months: int) -> date:
    """Kalendar oy qo'shadi. 31-yanvar + 1 oy = 28/29-fevral."""
    month = start.month - 1 + months
    year = start.year + month // 12
    month = month % 12 + 1
    # Keyingi oyning birinchi kunidan bir kun orqaga: o'sha oyning oxirgi kuni.
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    return date(year, month, min(start.day, last_day.day))


def offline_expiry(order: Order) -> datetime:
    """Offlayn abonement qachongacha ochiq bo'ladi.

    Amal qilayotgan abonement bo'lsa, yangi oylar uning ustiga qo'shiladi — o'quvchi
    muddat tugashini kutmasdan oldindan to'lashi mumkin.
    """
    now = timezone.now()
    current = access.open_enrollment(order.user, order.course)
    base = now
    if current is not None and current.expires_at and current.expires_at > now:
        base = current.expires_at
    target = add_months(base.date(), order.months)
    return base.replace(year=target.year, month=target.month, day=target.day)
