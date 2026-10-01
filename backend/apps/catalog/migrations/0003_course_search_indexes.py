"""Katalog qidiruvi uchun `pg_trgm` kengaytmasi va GIN indekslari.

Indekslar `RunSQL` bilan qo'shiladi: qidiriladigan ustunlar (`title_uz`, `title_ru`, ...) ni
modeltranslation ishga tushganda qo'shadi, shuning uchun ular model `Meta.indexes` da ko'rinmaydi.
"""

from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations

COLUMNS = ("title_uz", "title_ru", "title_en")


def index_operations() -> list[migrations.RunSQL]:
    operations = []
    for column in COLUMNS:
        name = f"catalog_course_{column}_trgm"
        operations.append(
            migrations.RunSQL(
                sql=(
                    f"CREATE INDEX IF NOT EXISTS {name} "
                    f"ON catalog_course USING gin ({column} gin_trgm_ops);"
                ),
                reverse_sql=f"DROP INDEX IF EXISTS {name};",
            )
        )
    return operations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_course_lesson_count_course_total_duration_min_module_and_more"),
    ]

    operations = [TrigramExtension(), *index_operations()]
