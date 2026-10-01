from django.db import migrations

# Rollar shu yerda qat'iy yozilgan: migratsiya keyingi kod o'zgarishlariga bog'liq bo'lmasligi kerak.
ROLES = ("STUDENT", "INSTRUCTOR", "MANAGER", "SUPPORT", "ADMIN")


def create_role_groups(apps, schema_editor):
    group_model = apps.get_model("auth", "Group")
    for name in ROLES:
        group_model.objects.get_or_create(name=name)


def delete_role_groups(apps, schema_editor):
    group_model = apps.get_model("auth", "Group")
    group_model.objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_role_groups, delete_role_groups),
    ]
