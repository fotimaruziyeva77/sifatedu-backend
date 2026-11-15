from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="integrations",
            name="telegram_leads_chat_id",
            field=models.CharField(blank=True, max_length=255, verbose_name="arizalar guruhi"),
        ),
        migrations.AlterField(
            model_name="integrations",
            name="telegram_reports_chat_id",
            field=models.CharField(blank=True, max_length=255, verbose_name="hisobot guruhi"),
        ),
        migrations.AlterField(
            model_name="integrations",
            name="click_service_id",
            field=models.CharField(blank=True, max_length=255, verbose_name="Click service ID"),
        ),
        migrations.AlterField(
            model_name="integrations",
            name="click_merchant_id",
            field=models.CharField(blank=True, max_length=255, verbose_name="Click merchant ID"),
        ),
        migrations.AlterField(
            model_name="integrations",
            name="click_merchant_user_id",
            field=models.CharField(blank=True, max_length=255, verbose_name="Click user ID"),
        ),
    ]
