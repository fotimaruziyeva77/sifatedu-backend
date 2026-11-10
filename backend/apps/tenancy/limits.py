"""Tarif cheklovlari: mavjud ma'lumot ishlaydi, yangisi qo'shilmaydi."""

from typing import Any

from django.core.cache import cache
from rest_framework import exceptions

from .access import current_center
from .models import Plan

GIB = 1024**3
UPGRADE_HINT = "Tarifni oshirish uchun platforma bilan bog'laning."
# Oxirgi hisobdan keyin yuklanganlar (bayt): `tasks.refresh_usage` har kecha nolga tushiradi.
PENDING_DISK_KEY = "disk:pending"
PENDING_DISK_TTL = 3 * 24 * 60 * 60


class LimitReached(exceptions.APIException):
    status_code = 403
    default_code = "limit_reached"
    default_detail = "Tarif chegarasiga yetildi."


def _plan() -> Plan | None:
    center = current_center()
    return center.plan if center else None


def _student_count() -> int:
    from apps.learning.models import Enrollment

    return (
        Enrollment.objects.filter(status=Enrollment.Status.ACTIVE)
        .values("user_id")
        .distinct()
        .count()
    )


def _staff_count() -> int:
    from apps.users.models import User

    return User.objects.filter(is_active=True, is_staff=True, is_superuser=False).count()


def check_new_student(user: Any) -> None:
    """Yangi yozilishdan oldin. Allaqachon o'qiyotgan odam yana bir kursga yozilsa — sanalmaydi."""
    from apps.learning.models import Enrollment

    plan = _plan()
    if plan is None or plan.max_students is None:
        return
    if Enrollment.objects.filter(user=user, status=Enrollment.Status.ACTIVE).exists():
        return
    if _student_count() >= plan.max_students:
        raise LimitReached(f"O'quvchilar soni tarif chegarasiga yetdi. {UPGRADE_HINT}")


def check_new_staff(user: Any) -> None:
    """Xodim roli berishdan oldin. Allaqachon xodim bo'lsa — sanalmaydi."""
    plan = _plan()
    if plan is None or plan.max_staff is None or user.is_staff or user.is_superuser:
        return
    if _staff_count() >= plan.max_staff:
        raise LimitReached(f"Xodimlar soni tarif chegarasiga yetdi. {UPGRADE_HINT}")


def check_disk(size: int = 0) -> None:
    """Yangi yuklashdan oldin. Hajm har kecha hisoblanadi (`tasks.refresh_usage`), undan keyin
    yuklanganlari `size` bo'yicha qo'shib boriladi: chegara kun davomida ham ishlaydi."""
    center = current_center()
    if center is None or center.plan is None or center.plan.max_disk_gb is None:
        return
    limit = center.plan.max_disk_gb * GIB
    used = center.disk_bytes + int(cache.get(PENDING_DISK_KEY, 0))
    if used >= limit or used + size > limit:
        raise LimitReached(f"Fayllar uchun joy tugadi. {UPGRADE_HINT}")
    if size > 0:
        cache.add(PENDING_DISK_KEY, 0, PENDING_DISK_TTL)
        cache.incr(PENDING_DISK_KEY, size)
