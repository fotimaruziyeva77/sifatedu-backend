import os
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "DJANGO_SUPERUSER_PHONE va DJANGO_SUPERUSER_PASSWORD bo'yicha superuser yaratadi, "
        "agar u hali yo'q bo'lsa. Faqat local muhit uchun."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        phone = os.environ.get("DJANGO_SUPERUSER_PHONE", "")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not phone or not password:
            self.stdout.write("Superuser o'zgaruvchilari berilmagan, o'tkazib yuborildi.")
            return

        user_model = get_user_model()
        if user_model.objects.filter(phone=phone).exists():
            self.stdout.write("Superuser allaqachon mavjud.")
            return

        user_model.objects.create_superuser(phone=phone, password=password, first_name="Admin")
        self.stdout.write(self.style.SUCCESS(f"Superuser yaratildi: {phone}"))
