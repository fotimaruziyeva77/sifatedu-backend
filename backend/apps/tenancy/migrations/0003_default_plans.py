from typing import Any

from django.db import migrations

# docs/saas-reja.md §2. Nom, narx, bo'lim va sonlar keyin platforma panelida o'zgaradi.
STANDARD = ["lessons", "bot", "click"]
PLANS = [
    {"name": "Start", "order": 1, "features": [], "max_students": 100, "max_staff": 5, "max_disk_gb": 1},
    {"name": "Standart", "order": 2, "features": STANDARD, "max_students": 500, "max_staff": 20, "max_disk_gb": 10},
    {
        "name": "Pro",
        "order": 3,
        "features": [*STANDARD, "exams", "placement", "rewards", "ai", "video"],
        "max_students": 2000,
        "max_staff": None,
        "max_disk_gb": 100,
    },
]


def create_plans(apps: Any, schema_editor: Any) -> None:
    Plan = apps.get_model("tenancy", "Plan")
    Center = apps.get_model("tenancy", "Center")
    plans = {item["name"]: Plan.objects.create(**item) for item in PLANS}
    # Ishlab turgan markaz (Sifat Edu) hamma bo'limini saqlab qoladi.
    Center.objects.exclude(schema_name="public").update(plan=plans["Pro"])


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0002_plans")]

    operations = [migrations.RunPython(create_plans, migrations.RunPython.noop)]
