"""Birinchi markazning bot, Click va Eskiz sozlamalari `.env`dan bazaga ko'chadi.

Faqat bir marta va faqat shu markazning sxemasida ishlaydi; boshqa markazlar qatori bo'sh qoladi.
"""

from typing import Any

from django.conf import settings
from django.db import migrations


def import_env(apps: Any, schema_editor: Any) -> None:
    if schema_editor.connection.schema_name != settings.FIRST_CENTER_SCHEMA:
        return
    apps.get_model("integrations", "Integrations").objects.update_or_create(
        pk=1,
        defaults={
            "telegram_token": settings.TELEGRAM_BOT_TOKEN,
            "telegram_username": settings.TELEGRAM_BOT_USERNAME.lstrip("@"),
            "telegram_webhook_secret": settings.TELEGRAM_WEBHOOK_SECRET,
            "telegram_leads_chat_id": settings.TELEGRAM_LEADS_CHAT_ID,
            "telegram_reports_chat_id": settings.TELEGRAM_REPORTS_CHAT_ID,
            "telegram_login": bool(settings.TELEGRAM_BOT_USERNAME),
            "click_service_id": settings.CLICK_SERVICE_ID,
            "click_merchant_id": settings.CLICK_MERCHANT_ID,
            "click_merchant_user_id": settings.CLICK_MERCHANT_USER_ID,
            "click_secret_key": settings.CLICK_SECRET_KEY,
            "click_tin": settings.CLICK_MERCHANT_TIN,
            "eskiz_email": settings.ESKIZ_EMAIL,
            "eskiz_password": settings.ESKIZ_PASSWORD,
            "eskiz_from": settings.ESKIZ_FROM,
            "eskiz_brand": settings.FIRST_CENTER_NAME,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("integrations", "0001_initial")]

    operations = [migrations.RunPython(import_env, migrations.RunPython.noop)]
