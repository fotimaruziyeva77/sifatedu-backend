"""Do'kon: sovg'a olish (coin yechiladi, zaxira kamayadi) va buyurtma holatlari.

Bir vaqtda ikki xarid bo'lsa ham balans manfiy bo'lmaydi va zaxira ortiqcha sotilmaydi:
sovg'a qatori va hamyon qulflanadi (`select_for_update`), coin `rewards.credit` orqali (u yetarli
bo'lmasa xato beradi). Bekor qilinsa — coin qaytadi, zaxira tiklanadi.
"""

from typing import Any

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import locale_of, text
from apps.rewards import services as rewards
from apps.rewards.models import Entry
from apps.users.models import User
from apps.users.roles import Role

from .models import Product, Purchase

Status = Purchase.Status
# Holat o'zgarishi: qayerdan qayerga o'tish mumkin.
FLOW = {
    Status.NEW: (Status.READY, Status.DELIVERED, Status.CANCELED),
    Status.READY: (Status.DELIVERED, Status.CANCELED),
    Status.DELIVERED: (),
    Status.CANCELED: (),
}


class ShopError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan sabab bilan (API 400)."""


def audiences(user: Any) -> list[str]:
    """Kimga ko'rinadi: hamma uchun va o'quvchining o'z ko'rinishi (kattalar yoki SIFAT Kids)."""
    audience = getattr(user, "audience", "ADULT") or "ADULT"
    return [Product.Audience.ALL, audience]


def catalog(user: Any) -> QuerySet[Product]:
    return Product.objects.filter(is_active=True, audience__in=audiences(user))


def buy(user: User, product_id: int) -> Purchase:
    with transaction.atomic():
        product = Product.objects.select_for_update().filter(pk=product_id).first()
        if product is None or not product.is_active:
            raise ShopError(_("Bu sovg'a sotuvda emas."))
        if product.audience not in audiences(user):
            raise ShopError(_("Bu sovg'a siz uchun emas."))
        if not product.in_stock:
            raise ShopError(_("Afsuski, bu sovg'a tugadi."))
        purchase = Purchase.objects.create(
            user=user, product=product, name=product.name, price=product.price
        )
        try:
            rewards.credit(
                user.pk,
                Entry.Reason.PURCHASE,
                key=f"shop:{purchase.pk}",
                coins=-product.price,
                note=product.name,
            )
        except rewards.RewardError as exc:
            raise ShopError(
                _("Coin yetarli emas: yana {count} coin kerak.").format(
                    count=product.price - rewards.wallet_of(user.pk).coins
                )
            ) from exc
        if product.stock is not None:
            product.stock -= 1
            product.save(update_fields=["stock", "updated_at"])
        transaction.on_commit(lambda: tell_managers(purchase.pk))
    return purchase


def set_status(
    purchase: Purchase, status: str, *, by: Any = None, note: str | None = None
) -> Purchase:
    """Holatni o'zgartiradi. Bekor qilinsa — coin qaytadi va zaxira tiklanadi. O'quvchiga xabar."""
    now = timezone.now()
    with transaction.atomic():
        locked = Purchase.objects.select_for_update().select_related("product").get(pk=purchase.pk)
        if status not in FLOW[Status(locked.status)]:
            raise ShopError(_("Buyurtma holatini bunday o'zgartirib bo'lmaydi."))
        locked.status = status
        locked.handled_by = by
        if note is not None:
            locked.note = note.strip()[:300]
        stamp = {
            Status.READY: "ready_at",
            Status.DELIVERED: "delivered_at",
            Status.CANCELED: "canceled_at",
        }[Status(status)]
        setattr(locked, stamp, now)
        locked.save()
        if status == Status.CANCELED:
            rewards.credit(
                locked.user_id,
                Entry.Reason.REFUND,
                key=f"shop-refund:{locked.pk}",
                coins=locked.price,
                note=locked.name,
            )
            product = Product.objects.select_for_update().get(pk=locked.product_id)
            if product.stock is not None:
                product.stock += 1
                product.save(update_fields=["stock", "updated_at"])
        transaction.on_commit(lambda: tell_student(locked.pk))
    return locked


def managers() -> QuerySet[User]:
    return User.objects.filter(
        Q(groups__name__in=[Role.MANAGER, Role.ADMIN]) | Q(is_superuser=True), is_active=True
    ).distinct()


def tell_managers(purchase_id: int) -> None:
    purchase = Purchase.objects.select_related("user").filter(pk=purchase_id).first()
    if purchase is None:
        return
    student = purchase.user.get_full_name() or purchase.user.phone
    for manager in managers():
        locale = locale_of(manager.locale)
        notify(
            manager,
            Notification.Kind.SHOP,
            title=text(locale, "shop_new_title", name=purchase.name),
            body=text(locale, "shop_new_body", student=student, price=str(purchase.price)),
            link=f"/admin/shop/purchase/{purchase.pk}/change/",
            dedupe_key=f"shop-new:{purchase.pk}:{manager.pk}",
        )


def tell_student(purchase_id: int) -> None:
    purchase = Purchase.objects.select_related("user").filter(pk=purchase_id).first()
    if purchase is None:
        return
    locale = locale_of(purchase.user.locale)
    with translation.override(locale):
        status = str(Status(purchase.status).label)
    body = text(locale, f"shop_{purchase.status.lower()}_body", price=str(purchase.price))
    if purchase.note:
        body = f"{body}\n{purchase.note}"
    notify(
        purchase.user,
        Notification.Kind.SHOP,
        title=text(locale, "shop_status_title", name=purchase.name, status=status),
        body=body,
        link="/dashboard/shop/orders",
        dedupe_key=f"shop:{purchase.pk}:{purchase.status}",
    )
