"""Bitta markazli eski bazani birinchi markazga aylantiradi.

Hamma jadval `public`dan markaz sxemasiga ko'chadi (`ALTER TABLE ... SET SCHEMA` — ma'lumot
nusxalanmaydi, sekundlar ichida), `public`da platforma jadvallari yangidan yaratiladi. Hammasi
bitta tranzaksiyada: xato bo'lsa baza avvalgi holatida qoladi. Tartib: docs/saas-kochirish.md
"""

from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django_tenants.utils import get_public_schema_name, schema_exists

from apps.tenancy.db import connection
from apps.tenancy.services import ensure_center, ensure_platform

# Eski bazaning belgisi: foydalanuvchilar `public`da, markazlar jadvali esa hali yo'q.
LEGACY_TABLE = "users_user"
CENTER_TABLE = "tenancy_center"


def public_relations() -> dict[str, list[str]]:
    """`public`dagi kengaytmaga tegishli bo'lmagan obyektlar turi bo'yicha."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname, c.relkind
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND NOT EXISTS (
                SELECT 1 FROM pg_depend d
                WHERE d.objid = c.oid AND d.deptype = 'e'
              )
            ORDER BY c.relname
            """,
            [get_public_schema_name()],
        )
        relations: dict[str, list[str]] = {}
        for name, kind in cursor.fetchall():
            relations.setdefault(kind, []).append(name)
    return relations


def row_count(schema: str, table: str) -> int:
    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        # Nomlar foydalanuvchidan emas — `pg_class`dan va sozlamadan.
        cursor.execute(f"SELECT count(*) FROM {quote(schema)}.{quote(table)}")  # noqa: S608
        return int(cursor.fetchone()[0])


class Command(BaseCommand):
    help = "Eski bazadagi hamma jadvalni birinchi markaz sxemasiga ko'chiradi."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Faqat tekshiradi: baza ko'chirilmagan bo'lsa, xato bilan chiqadi.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        connection.set_schema_to_public()
        tables = public_relations().get("r", [])
        pending = LEGACY_TABLE in tables and CENTER_TABLE not in tables
        if options["check"]:
            if pending:
                raise CommandError(
                    "Baza hali bitta markazli: migratsiya o'tkazilmaydi. "
                    "Avval `manage.py adopt_center` (docs/saas-kochirish.md)."
                )
            return
        if not pending:
            raise CommandError("Ko'chiradigan narsa yo'q: baza bo'sh yoki allaqachon ko'chirilgan.")
        self.adopt(settings.FIRST_CENTER_SCHEMA)

    def adopt(self, schema: str) -> None:
        relations = public_relations()
        tables = relations.pop("r", [])
        if relations:
            # Ko'rinish va bo'lingan jadvallarni bu buyruq ko'chirmaydi — jim o'tkazib bo'lmaydi.
            raise CommandError(f"`public`da kutilmagan obyektlar bor: {relations}")
        if schema_exists(schema):
            raise CommandError(f"`{schema}` sxemasi allaqachon bor.")

        quote = connection.ops.quote_name
        public = get_public_schema_name()
        with transaction.atomic():
            before = {table: row_count(public, table) for table in tables}
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE SCHEMA {quote(schema)}")
                for table in tables:
                    cursor.execute(
                        f"ALTER TABLE {quote(public)}.{quote(table)} SET SCHEMA {quote(schema)}"
                    )
            self.stdout.write(f"Ko'chirildi: {len(tables)} jadval")

            call_command("migrate_schemas", shared=True, interactive=False, verbosity=0)
            connection.set_schema_to_public()
            ensure_platform(settings.PLATFORM_DOMAIN)
            ensure_center(schema, settings.FIRST_CENTER_NAME, settings.FIRST_CENTER_DOMAINS)

            after = {table: row_count(schema, table) for table in tables}
            if before != after:
                raise CommandError("Qator soni o'zgardi: bekor qilindi.")
        self.stdout.write(
            self.style.SUCCESS(f"Tayyor: {schema}, jami {sum(after.values())} qator.")
        )
