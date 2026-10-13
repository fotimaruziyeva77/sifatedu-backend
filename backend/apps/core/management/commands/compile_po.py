from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.core import po


class Command(BaseCommand):
    help = (
        "Loyiha tarjimalarini (LOCALE_PATHS ichidagi .po) .mo ga yig'adi — gettext kerak emas. "
        "--check: .mo eskirgan bo'lsa xato bilan chiqadi."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--check", action="store_true", help="Faqat tekshirish.")

    def handle(self, *args: Any, **options: Any) -> None:
        stale = []
        for po_path in po.po_files():
            mo_path = po_path.with_suffix(".mo")
            data = po.compiled(po_path)
            if mo_path.exists() and mo_path.read_bytes() == data:
                continue
            if options["check"]:
                stale.append(str(mo_path))
                continue
            mo_path.write_bytes(data)
            self.stdout.write(self.style.SUCCESS(f"Yangilandi: {mo_path}"))
        if stale:
            raise CommandError("Eskirgan .mo (python manage.py compile_po): " + ", ".join(stale))
