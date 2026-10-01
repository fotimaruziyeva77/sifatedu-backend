"""Rollar va ruxsatlar (TZ 3.1–3.2).

Rol — Django guruhi (nomi rol kodi). Kim nima qila olishi shu fayldagi jadvalda: `migrate`dan
keyin guruhlar va ruxsatlar avtomatik sinxronlanadi (`sync_role_groups`), qo'lda o'zgartirish
kerak emas. Xodim rollari admin panelga kirishni (`is_staff`) o'zi beradi — signals.py.
"""

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from .models import User


class Role(models.TextChoices):
    STUDENT = "STUDENT", _("O'quvchi")
    TEACHER = "TEACHER", _("O'qituvchi")
    MANAGER = "MANAGER", _("Menejer")
    DIRECTOR = "DIRECTOR", _("Direktor")
    ADMIN = "ADMIN", _("Admin")


# Admin panelga kiradiganlar.
STAFF_ROLES = frozenset({Role.TEACHER, Role.MANAGER, Role.DIRECTOR, Role.ADMIN})
# Barcha kurslar, guruhlar va o'quvchilarni ko'radiganlar (o'qituvchi — faqat o'zinikini).
SEES_ALL_ROLES = (Role.ADMIN, Role.MANAGER, Role.DIRECTOR)
# Direktor ko'radigan bo'limlar (faqat o'qish).
DIRECTOR_APPS = (
    "assistant",
    "auditlog",
    "bot",
    "catalog",
    "certificates",
    "content",
    "exams",
    "homework",
    "leads",
    "learning",
    "live",
    "notifications",
    "payments",
    "quizzes",
    "rewards",
    "shop",
    # Kunlik statistika (admin bosh sahifasi): `view_statistics`.
    "stats",
    "users",
    "videos",
)


def _perms(app: str, model: str, *actions: str) -> list[str]:
    return [f"{app}.{action}_{model}" for action in actions]


ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.STUDENT: [],
    # O'z kurslarining mazmuni: modul, dars, material, video. Narx va nashr — Admin'da.
    Role.TEACHER: [
        *_perms("catalog", "course", "view"),
        *_perms("catalog", "module", "view", "add", "change"),
        *_perms("catalog", "lesson", "view", "add", "change"),
        *_perms("catalog", "lessonmaterial", "view", "add", "change", "delete"),
        *_perms("videos", "videoasset", "view", "add", "change"),
        *_perms("learning", "studygroup", "view"),
        # Uy vazifasi: o'z kurslari darslariga (dars sahifasida) va javoblarni ko'rish.
        *_perms("homework", "assignment", "view", "add", "change", "delete"),
        *_perms("homework", "submission", "view"),
        # Testlar: o'z kurslari darslariga savollar va natijalarni ko'rish.
        *_perms("quizzes", "quiz", "view", "add", "change", "delete"),
        *_perms("quizzes", "question", "view", "add", "change", "delete"),
        *_perms("quizzes", "choice", "view", "add", "change", "delete"),
        *_perms("quizzes", "attempt", "view"),
        # Jonli darslar: o'z guruhlari darslari va davomati; jadvalni menejer qo'yadi.
        *_perms("live", "livelesson", "view", "add", "change"),
        *_perms("live", "attendance", "view", "change"),
        *_perms("live", "scheduleslot", "view"),
        *_perms("live", "grouplesson", "view"),
        # Oylik imtihon: o'z kurslariga tayyorlaydi (topshiriqlar, modullar); baholash — kabinetda.
        *_perms("exams", "exam", "view", "add", "change"),
        *_perms("exams", "examtask", "view", "add", "change", "delete"),
        *_perms("exams", "examresult", "view"),
        *_perms("certificates", "certificate", "view"),
    ],
    Role.MANAGER: [
        *_perms("leads", "lead", "view", "add", "change"),
        *_perms("assistant", "conversation", "view", "change"),
        *_perms("assistant", "assistantsettings", "view"),
        *_perms("users", "user", "view", "add", "change"),
        *_perms("users", "onetimecode", "view"),
        *_perms("learning", "enrollment", "view", "add", "change"),
        *_perms("learning", "studygroup", "view", "add", "change"),
        *_perms("learning", "lessonprogress", "view"),
        *_perms("payments", "order", "view"),
        *_perms("payments", "paymenttransaction", "view"),
        *_perms("payments", "refund", "view", "add"),
        *_perms("catalog", "course", "view"),
        *_perms("catalog", "module", "view"),
        *_perms("catalog", "lesson", "view"),
        *_perms("catalog", "category", "view"),
        *_perms("catalog", "instructor", "view"),
        # Kunlik statistika va o'quvchilarga xabar yuborish.
        *_perms("stats", "statistics", "view"),
        *_perms("notifications", "broadcast", "view", "add", "change", "send"),
        *_perms("notifications", "notification", "view"),
        *_perms("homework", "assignment", "view"),
        *_perms("homework", "submission", "view"),
        *_perms("quizzes", "quiz", "view"),
        *_perms("quizzes", "question", "view"),
        *_perms("quizzes", "choice", "view"),
        *_perms("quizzes", "attempt", "view"),
        *_perms("live", "livelesson", "view", "add", "change", "delete"),
        *_perms("live", "attendance", "view", "change"),
        *_perms("live", "scheduleslot", "view", "add", "change", "delete"),
        *_perms("live", "grouplesson", "view", "add", "change", "delete"),
        # Telegram bot: foydalanuvchilar (faqat ko'rish) va majburiy obuna kanallari.
        *_perms("bot", "botchat", "view"),
        *_perms("bot", "requiredchannel", "view", "add", "change", "delete"),
        *_perms("exams", "exam", "view", "add", "change", "delete"),
        *_perms("exams", "examtask", "view", "add", "change", "delete"),
        *_perms("exams", "examresult", "view"),
        *_perms("certificates", "certificate", "view", "change"),
        # XP va coin: tarix (qo'lda qo'shish, bekor qilish), hamyonlar, topshiriqlar, kuponlar.
        # Qiymatlar (sozlamalar) — faqat admin.
        *_perms("rewards", "entry", "view", "add", "change"),
        *_perms("rewards", "wallet", "view"),
        *_perms("rewards", "dailytask", "view"),
        *_perms("rewards", "coupon", "view", "add"),
        *_perms("rewards", "gamesettings", "view"),
        # Do'kon: sovg'alar va buyurtmalar (holat: tayyor, topshirildi, bekor).
        *_perms("shop", "product", "view", "add", "change"),
        *_perms("shop", "purchase", "view", "change"),
    ],
    # DIRECTOR va ADMIN ro'yxati bazadan hisoblanadi: `permissions_for`.
    Role.DIRECTOR: [],
    Role.ADMIN: [],
}


def permissions_for(role: str) -> Any:
    """Rolning ruxsatlari (Permission queryset)."""
    if role == Role.ADMIN:
        return Permission.objects.all()
    if role == Role.DIRECTOR:
        return Permission.objects.filter(
            codename__startswith="view_", content_type__app_label__in=DIRECTOR_APPS
        )
    pairs = [name.split(".", 1) for name in ROLE_PERMISSIONS[role]]
    query = models.Q(pk__in=[])
    for app_label, codename in pairs:
        query |= models.Q(content_type__app_label=app_label, codename=codename)
    return Permission.objects.filter(query)


def sync_role_groups() -> None:
    """Guruhlarni yaratadi va ruxsatlarini jadvalga moslaydi (qayta-qayta chaqirish xavfsiz)."""
    from django.contrib.auth.management import create_permissions

    # Boshqa app'larning ruxsatlari hali yaratilmagan bo'lishi mumkin (post_migrate tartibi).
    for app_config in apps.get_app_configs():
        create_permissions(app_config, verbosity=0)
    for role in Role:
        group, _created = Group.objects.get_or_create(name=role.value)
        group.permissions.set(permissions_for(role.value))


def role_names(user: "User") -> set[str]:
    """Foydalanuvchining rollari. Superuser — har doim Admin. So'rov davomida keshlanadi."""
    cached: set[str] | None = getattr(user, "_role_cache", None)
    if cached is None:
        # `groups.all()` — oldindan yuklangan bo'lsa (prefetch_related), so'rov yuborilmaydi.
        cached = {group.name for group in user.groups.all() if group.name in Role.values}
        if user.is_superuser:
            cached.add(Role.ADMIN)
        user._role_cache = cached  # type: ignore[attr-defined]
    return set(cached)


def has_role(user: Any, *roles: str) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return bool(role_names(user) & set(roles))


def sees_all(user: Any) -> bool:
    """Barcha kurslarni ko'radimi (aks holda — faqat o'qituvchi sifatida biriktirilganlarini)."""
    return has_role(user, *SEES_ALL_ROLES)


def set_roles(user: "User", roles: Iterable[str]) -> None:
    """Rollarni almashtiradi; rolga tegishli bo'lmagan boshqa guruhlar saqlanadi.
    `is_staff` guruhlar o'zgarganda signal orqali qayta hisoblanadi (signals.py)."""
    wanted = {Role(role).value for role in roles}
    current = set(user.groups.filter(name__in=Role.values).values_list("name", flat=True))
    if remove := current - wanted:
        user.groups.remove(*Group.objects.filter(name__in=remove))
    if add := wanted - current:
        if Group.objects.filter(name__in=add).count() < len(add):
            sync_role_groups()
        user.groups.add(*Group.objects.filter(name__in=add))
    user.__dict__.pop("_role_cache", None)
