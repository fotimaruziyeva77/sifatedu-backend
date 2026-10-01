"""Hamyon: XP va coin qo'shish, shtraf, bekor qilish.

Har o'zgarish `Entry` bilan va `key` bo'yicha bir marta (masalan, `lesson:<user>:<lesson>`):
hodisa ikki marta kelsa ham mukofot bitta. Shtraf XP'ni 0 dan pastga tushirmaydi — aslida
yechilgani `applied_xp` da, bekor qilinganda aynan shu qaytariladi.
"""

import logging
from collections.abc import Callable
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.learning.models import Enrollment, StudyGroup
from apps.users.roles import sees_all

from .models import Entry, GameSettings, Wallet

logger = logging.getLogger(__name__)


class RewardError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan sabab bilan (API 400)."""


def wallet_of(user_id: int) -> Wallet:
    wallet, _created = Wallet.objects.get_or_create(user_id=user_id)
    return wallet


def credit(
    user_id: int,
    reason: str,
    *,
    key: str,
    xp: int = 0,
    coins: int = 0,
    course_id: int | None = None,
    note: str = "",
    by: Any = None,
) -> Entry | None:
    """Mukofot (musbat) yoki shtraf (manfiy XP). Shu `key` bilan faol yozuv bor bo'lsa — None."""
    with transaction.atomic():
        wallet_of(user_id)
        wallet = Wallet.objects.select_for_update().get(user_id=user_id)
        if Entry.objects.filter(key=key, canceled_at__isnull=True).exists():
            return None
        if coins < 0 and wallet.coins < -coins:
            raise RewardError(_("Coin yetarli emas."))
        applied = xp if xp >= 0 else -min(-xp, wallet.xp)
        try:
            with transaction.atomic():
                entry = Entry.objects.create(
                    user_id=user_id,
                    reason=reason,
                    xp=xp,
                    applied_xp=applied,
                    coins=coins,
                    key=key[:100],
                    course_id=course_id,
                    note=note[:200],
                    created_by=by,
                )
        except IntegrityError:
            # Parallel kelgan xuddi shu hodisa: ikkinchisi yozilmaydi.
            return None
        wallet.xp += applied
        wallet.coins += coins
        wallet.save(update_fields=["xp", "coins", "updated_at"])
    return entry


def reward(user_id: int, reason: str, points: int, *, key: str, **extra: Any) -> Entry | None:
    """Harakat uchun mukofot: XP va unga teng coin."""
    if points <= 0:
        return None
    return credit(user_id, reason, key=key, xp=points, coins=points, **extra)


def penalize(user_id: int, reason: str, points: int, *, key: str, **extra: Any) -> Entry | None:
    """Shtraf — faqat XP'dan."""
    if points <= 0:
        return None
    return credit(user_id, reason, key=key, xp=-points, **extra)


def cancel(entry: Entry, *, by: Any = None, reason: str = "") -> Entry:
    """Yozuvni bekor qiladi: hamyonga aynan yechilgan/qo'shilgani qaytadi."""
    with transaction.atomic():
        locked = Entry.objects.select_for_update().get(pk=entry.pk)
        if locked.canceled_at is not None:
            raise RewardError(_("Bu yozuv allaqachon bekor qilingan."))
        wallet_of(locked.user_id)
        wallet = Wallet.objects.select_for_update().get(user_id=locked.user_id)
        wallet.xp = max(0, wallet.xp - locked.applied_xp)
        wallet.coins = max(0, wallet.coins - locked.coins)
        wallet.save(update_fields=["xp", "coins", "updated_at"])
        locked.canceled_at = timezone.now()
        locked.canceled_by = by
        locked.cancel_reason = reason.strip()[:300]
        locked.save(update_fields=["canceled_at", "canceled_by", "cancel_reason"])
    return locked


def active(key: str) -> Entry | None:
    return Entry.objects.filter(key=key, canceled_at__isnull=True).first()


def can_cancel(user: Any, entry: Entry) -> bool:
    """Shtrafni bekor qilish: admin (hammasini) yoki o'qituvchi (o'z guruhi o'quvchisinikini)."""
    if not entry.is_penalty or entry.canceled_at is not None:
        return False
    if not getattr(user, "is_authenticated", False):
        return False
    if sees_all(user):
        return True
    groups = StudyGroup.objects.filter(teacher=user).values("pk")
    return Enrollment.objects.filter(user_id=entry.user_id, group__in=groups).exists()


def safely(handler: Callable[..., Any]) -> Callable[..., None]:
    """Hodisa tinglovchisi: mukofotdagi xato o'qish jarayonini (dars, test, vazifa) buzmasin."""

    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            with transaction.atomic():
                handler(*args, **kwargs)
        except Exception:
            logger.exception("Mukofot hisoblanmadi: %s", handler.__name__)

    wrapper.__name__ = handler.__name__
    return wrapper


def settings() -> GameSettings:
    return GameSettings.load()
