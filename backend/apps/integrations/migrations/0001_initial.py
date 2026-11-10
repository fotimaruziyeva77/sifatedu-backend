from django.db import migrations, models

import apps.integrations.fields


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="Integrations",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "telegram_token",
                    apps.integrations.fields.SecretField(
                        blank=True, default="", verbose_name="bot tokeni"
                    ),
                ),
                (
                    "telegram_username",
                    models.CharField(blank=True, max_length=64, verbose_name="bot nomi"),
                ),
                (
                    "telegram_webhook_secret",
                    apps.integrations.fields.SecretField(
                        blank=True, default="", verbose_name="webhook siri"
                    ),
                ),
                (
                    "telegram_leads_chat_id",
                    models.CharField(blank=True, max_length=32, verbose_name="arizalar guruhi"),
                ),
                (
                    "telegram_reports_chat_id",
                    models.CharField(blank=True, max_length=32, verbose_name="hisobot guruhi"),
                ),
                (
                    "telegram_login",
                    models.BooleanField(
                        default=False,
                        help_text="BotFather'da /setdomain qilingandan keyin yoqiladi.",
                        verbose_name="saytda Telegram orqali kirish",
                    ),
                ),
                (
                    "click_service_id",
                    models.CharField(blank=True, max_length=32, verbose_name="Click service ID"),
                ),
                (
                    "click_merchant_id",
                    models.CharField(blank=True, max_length=32, verbose_name="Click merchant ID"),
                ),
                (
                    "click_merchant_user_id",
                    models.CharField(blank=True, max_length=32, verbose_name="Click user ID"),
                ),
                (
                    "click_secret_key",
                    apps.integrations.fields.SecretField(
                        blank=True, default="", verbose_name="Click maxfiy kaliti"
                    ),
                ),
                ("click_tin", models.CharField(blank=True, max_length=20, verbose_name="STIR")),
                (
                    "eskiz_email",
                    models.CharField(blank=True, max_length=254, verbose_name="Eskiz email"),
                ),
                (
                    "eskiz_password",
                    apps.integrations.fields.SecretField(
                        blank=True, default="", verbose_name="Eskiz paroli"
                    ),
                ),
                (
                    "eskiz_from",
                    models.CharField(blank=True, max_length=20, verbose_name="SMS jo'natuvchi"),
                ),
                (
                    "eskiz_brand",
                    models.CharField(blank=True, max_length=200, verbose_name="SMS'dagi nom"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="yangilangan")),
            ],
            options={
                "verbose_name": "markaz kalitlari",
                "verbose_name_plural": "markaz kalitlari",
            },
        ),
    ]
