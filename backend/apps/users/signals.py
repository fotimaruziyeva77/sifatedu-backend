"""Rollar: `migrate`dan keyin guruhlar sinxronlanadi, rol o'zgarsa `is_staff` unga ergashadi."""

from typing import Any

from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import User
from .roles import STAFF_ROLES, role_names, sync_role_groups


def sync_after_migrate(sender: Any, **kwargs: Any) -> None:
    sync_role_groups()


@receiver(m2m_changed, sender=User.groups.through)
def _staff_follows_roles(
    sender: Any, instance: Any, action: str, reverse: bool, pk_set: set[int] | None, **kwargs: Any
) -> None:
    """Xodim roli bor — admin panelga kira oladi; roli olib tashlansa — kira olmaydi."""
    if action not in ("post_add", "post_remove"):
        return
    users = User.objects.filter(pk__in=pk_set or []) if reverse else [instance]
    for user in users:
        user.__dict__.pop("_role_cache", None)
        staff = bool(role_names(user) & STAFF_ROLES)
        if user.is_staff != staff:
            User.objects.filter(pk=user.pk).update(is_staff=staff)
            user.is_staff = staff
