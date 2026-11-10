"""AI budjeti: Pro tarifga boshlang'ich chegara, birinchi markazda hozirgi budjet o'zgarmaydi."""

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import migrations

PRO_MONTHLY = Decimal("10")
# Birinchi markazning o'z budjeti `AssistantSettings`da: tarif uni kamaytirmasin.
FIRST_CENTER_MONTHLY = Decimal("1000")


def set_budgets(apps: Any, schema_editor: Any) -> None:
    apps.get_model("tenancy", "Plan").objects.filter(name="Pro").update(ai_monthly_usd=PRO_MONTHLY)
    apps.get_model("tenancy", "Center").objects.filter(
        schema_name=settings.FIRST_CENTER_SCHEMA
    ).update(ai_monthly_usd=FIRST_CENTER_MONTHLY)


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0004_step25")]

    operations = [migrations.RunPython(set_budgets, migrations.RunPython.noop)]
