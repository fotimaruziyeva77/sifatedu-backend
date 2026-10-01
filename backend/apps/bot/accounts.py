"""Botda ro'yxatdan o'tish va akkauntni ulash.

Telefonni Telegram'ning o'zi tasdiqlaydi (kontakt — yozayotgan odamning o'z raqami), shuning
uchun SMS kerak emas. Bir raqam — bitta akkaunt: raqam saytda bor bo'lsa, shu akkauntga ulanadi.
Xodim akkaunti kontakt orqali ulanmaydi: kimdir xodimning raqamini qo'lga kiritsa ham, admin
panelga yo'l ochilmasin (xodim Telegram'ni saytdagi kabinetdan ulaydi).
"""

from enum import StrEnum
from typing import Any

from django.db import transaction

from apps.users import services
from apps.users.models import SocialAccount, User
from apps.users.social import SocialProfile

TELEGRAM = SocialAccount.Provider.TELEGRAM


class Outcome(StrEnum):
    CREATED = "created"
    LINKED = "linked"
    STAFF = "staff"
    BLOCKED = "blocked"


def is_staff_account(user: User) -> bool:
    return bool(user.is_staff or user.is_superuser)


def linked_user(chat_id: int) -> User | None:
    """Shu Telegram ulangan faol akkaunt (sayt bilan bitta manba — `SocialAccount`)."""
    account = (
        SocialAccount.objects.filter(provider=TELEGRAM, uid=str(chat_id))
        .select_related("user")
        .first()
    )
    if account is None or not account.user.is_active:
        return None
    return account.user


def profile_of(sender: dict[str, Any]) -> SocialProfile:
    return SocialProfile(
        provider=TELEGRAM,
        uid=str(sender["id"]),
        first_name=str(sender.get("first_name") or "")[:150],
        last_name=str(sender.get("last_name") or "")[:150],
    )


def attach(user: User, sender: dict[str, Any]) -> None:
    """Telegram'ni akkauntga ulaydi. Akkauntda boshqa Telegram bo'lsa — almashtiriladi
    (bir akkaunt — bitta Telegram)."""
    uid = str(sender["id"])
    SocialAccount.objects.filter(provider=TELEGRAM, user=user).exclude(uid=uid).delete()
    services.link_social(user, profile_of(sender))
    SocialAccount.objects.filter(provider=TELEGRAM, uid=uid).update(notify=True, blocked_at=None)


@transaction.atomic
def register(
    phone: str, sender: dict[str, Any], locale: str, referral_code: str = ""
) -> tuple[Outcome, User | None]:
    """Kontakt yuborildi: yangi akkaunt yoki mavjudiga ulash. Chaqiruvchi shu Telegram hali hech
    qaysi akkauntga ulanmaganini tekshirgan bo'ladi."""
    existing = User.objects.select_for_update().filter(phone=phone).first()
    if existing is not None:
        if not existing.is_active:
            return Outcome.BLOCKED, None
        if is_staff_account(existing):
            return Outcome.STAFF, None
        attach(existing, sender)
        return Outcome.LINKED, existing
    user = services.create_social_user(
        profile_of(sender), phone, locale, referred_by=services.referrer(referral_code)
    )
    return Outcome.CREATED, user
