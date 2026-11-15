"""Birinchi markazning bot, Click va Eskiz sozlamalari `.env`dan bazaga ko'chadi.

Faqat bir marta va faqat shu markazning sxemasida ishlaydi; boshqa markazlar qatori bo'sh qoladi.
Maydonga sig'maydigan qiymat ko'chirilmaydi (logda yoziladi): `.env`dagi kutilmagan qiymat
deploy'ni to'xtatmasin, uni keyin kabinetdagi «Markaz sozlamalari»da kiritish mumkin.
"""

from typing import Any

from django.conf import settings
from django.db import migrations


def env_values() -> dict[str, Any]:
    return {
        "telegram_token": settings.TELEGRAM_BOT_TOKEN,
        "telegram_username": settings.TELEGRAM_BOT_USERNAME.strip().lstrip("@"),
        "telegram_webhook_secret": settings.TELEGRAM_WEBHOOK_SECRET,
        "telegram_leads_chat_id": settings.TELEGRAM_LEADS_CHAT_ID.strip(),
        "telegram_reports_chat_id": settings.TELEGRAM_REPORTS_CHAT_ID.strip(),
        "telegram_login": bool(settings.TELEGRAM_BOT_USERNAME.strip()),
        "click_service_id": settings.CLICK_SERVICE_ID.strip(),
        "click_merchant_id": settings.CLICK_MERCHANT_ID.strip(),
        "click_merchant_user_id": settings.CLICK_MERCHANT_USER_ID.strip(),
        "click_secret_key": settings.CLICK_SECRET_KEY,
        "click_tin": settings.CLICK_MERCHANT_TIN.strip(),
        "eskiz_email": settings.ESKIZ_EMAIL.strip(),
        "eskiz_password": settings.ESKIZ_PASSWORD,
        "eskiz_from": settings.ESKIZ_FROM.strip(),
        "eskiz_brand": settings.FIRST_CENTER_NAME,
    }


def import_env(apps: Any, schema_editor: Any) -> None:
    if schema_editor.connection.schema_name != settings.FIRST_CENTER_SCHEMA:
        return
    model = apps.get_model("integrations", "Integrations")
    defaults = {}
    for name, value in env_values().items():
        limit = getattr(model._meta.get_field(name), "max_length", None)
        if isinstance(value, str) and limit and len(value) > limit:
            # Qiymatning o'zi logga yozilmaydi: unda maxfiy narsa bo'lishi mumkin.
            print(f"  integrations: {name} ko'chirilmadi — .env'da {len(value)} belgi (> {limit})")
            continue
        defaults[name] = value
    model.objects.update_or_create(pk=1, defaults=defaults)


class Migration(migrations.Migration):
    dependencies = [("integrations", "0002_longer_ids")]

    operations = [migrations.RunPython(import_env, migrations.RunPython.noop)]
