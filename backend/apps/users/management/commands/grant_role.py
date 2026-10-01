"""Foydalanuvchiga rol berish yoki olib tashlash (admin panelsiz, masalan, birinchi xodimlar uchun).

python manage.py grant_role +998901234567 TEACHER
python manage.py grant_role +998901234567 MANAGER --remove
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.core.phone import InvalidPhoneError, normalize_phone
from apps.users.models import User
from apps.users.roles import Role, role_names, set_roles


class Command(BaseCommand):
    help = "Foydalanuvchiga rol beradi (--remove bilan — olib tashlaydi)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("phone")
        parser.add_argument("role", choices=Role.values)
        parser.add_argument("--remove", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            phone = normalize_phone(options["phone"])
        except InvalidPhoneError as exc:
            raise CommandError("Telefon raqami noto'g'ri.") from exc
        user = User.objects.filter(phone=phone).first()
        if user is None:
            raise CommandError(f"{phone} raqamli foydalanuvchi yo'q.")
        # Haqiqiy guruhlar (superuser'ning "virtual" Admin roli emas).
        roles = set(user.groups.filter(name__in=Role.values).values_list("name", flat=True))
        roles = roles - {options["role"]} if options["remove"] else roles | {options["role"]}
        set_roles(user, roles)
        user.refresh_from_db()
        labels = ", ".join(str(Role(role).label) for role in sorted(role_names(user))) or "—"
        self.stdout.write(self.style.SUCCESS(f"{phone}: {labels} (admin panel: {user.is_staff})"))
