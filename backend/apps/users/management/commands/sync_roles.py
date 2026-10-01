"""Rollar jadvalini (roles.py) bazaga qo'llash. `migrate` buni o'zi qiladi; bu — qo'lda ishga
tushirish uchun (masalan, ruxsatlar jadvali o'zgargan, lekin migratsiya yo'q)."""

from typing import Any

from django.core.management.base import BaseCommand

from apps.users.roles import Role, permissions_for, sync_role_groups


class Command(BaseCommand):
    help = "Rol guruhlari va ruxsatlarini roles.py jadvaliga moslaydi."

    def handle(self, *args: Any, **options: Any) -> None:
        sync_role_groups()
        for role in Role:
            self.stdout.write(f"{role.label}: {permissions_for(role.value).count()} ta ruxsat")
