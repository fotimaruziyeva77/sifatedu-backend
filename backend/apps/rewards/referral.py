"""Referal mukofotlari: do'st birinchi darsni tugatsa va to'lov qilsa — taklif qilganga coin
va kupon; do'stning birinchi to'loviga chegirma.

Chegirma buyurtma yaratilganda hisoblanadi (Click'ka boradigan summa shu). Bitta buyurtmaga
bitta chegirma: do'stning birinchi to'lovi yoki eng eski kupon.
"""

from dataclasses import dataclass
from typing import Any

from django.utils import timezone, translation

from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import locale_of, text
from apps.payments.models import Order
from apps.users.models import User

from . import services
from .models import Coupon, Entry
from .rating import short_name


@dataclass(frozen=True)
class Discount:
    percent: int
    reason: str  # "REFERRAL" | "COUPON"
    coupon: Coupon | None = None

    def apply(self, amount: int) -> int:
        """Chegirmali summa (so'm, butun)."""
        return max(0, amount - amount * self.percent // 100)


def discount_for(user: Any) -> Discount | None:
    if not getattr(user, "is_authenticated", False):
        return None
    config = services.settings()
    paid = Order.objects.filter(user_id=user.pk, status=Order.Status.PAID).exists()
    if user.referred_by_id and config.referral_discount and not paid:
        return Discount(config.referral_discount, "REFERRAL")
    coupon = (
        Coupon.objects.filter(user_id=user.pk, used_at__isnull=True)
        .exclude(order__status=Order.Status.PAID)
        .order_by("created_at", "pk")
        .first()
    )
    if coupon is not None:
        return Discount(coupon.percent, "COUPON", coupon)
    return None


def attach(order: Order, discount: Discount | None) -> None:
    """Kupon shu buyurtmaga biriktiriladi (to'langanda — ishlatilgan)."""
    if discount is not None and discount.coupon is not None:
        Coupon.objects.filter(pk=discount.coupon.pk, used_at__isnull=True).update(order=order)


def tell(referrer: User, key: str, friend: User, **values: Any) -> None:
    locale = locale_of(referrer.locale)
    with translation.override(locale):
        notify(
            referrer,
            Notification.Kind.REWARD,
            title=text(locale, f"{key}_title", friend=short_name(friend), **values),
            body=text(locale, f"{key}_body", friend=short_name(friend), **values),
            link="/dashboard/rewards",
            dedupe_key=f"{key}:{friend.pk}",
        )


def friend_lesson(user_id: int) -> None:
    """Do'st birinchi darsni tugatdi — taklif qilganga coin (bir marta)."""
    friend = User.objects.filter(pk=user_id).select_related("referred_by").first()
    if friend is None or friend.referred_by is None or not friend.referred_by.is_active:
        return
    points = services.settings().referral_lesson_coins
    entry = services.credit(
        friend.referred_by.pk,
        Entry.Reason.REFERRAL,
        key=f"referral:{friend.pk}",
        coins=points,
        note=short_name(friend),
    )
    if entry is not None and points:
        tell(friend.referred_by, "referral_lesson", friend, coins=str(points))


def order_paid(order: Order) -> None:
    """To'lov: kupon ishlatildi; do'stning birinchi to'lovi bo'lsa — taklif qilganga coin va
    kupon."""
    now = timezone.now()
    Coupon.objects.filter(order=order, used_at__isnull=True).update(used_at=order.paid_at or now)
    friend = User.objects.filter(pk=order.user_id).select_related("referred_by").first()
    if friend is None or friend.referred_by is None or not friend.referred_by.is_active:
        return
    first = (
        not Order.objects.filter(user=friend, status=Order.Status.PAID)
        .exclude(pk=order.pk)
        .exists()
    )
    if not first:
        return
    config = services.settings()
    entry = services.credit(
        friend.referred_by.pk,
        Entry.Reason.REFERRAL_PAID,
        key=f"referral-paid:{friend.pk}",
        coins=config.referral_paid_coins,
        note=short_name(friend),
    )
    if entry is None:
        return
    if config.coupon_percent:
        Coupon.objects.create(user=friend.referred_by, percent=config.coupon_percent, friend=friend)
    tell(
        friend.referred_by,
        "referral_paid",
        friend,
        coins=str(config.referral_paid_coins),
        percent=str(config.coupon_percent),
    )
