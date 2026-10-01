from django.apps import AppConfig
from django.db.models.signals import post_migrate


class UsersConfig(AppConfig):
    name = "apps.users"
    verbose_name = "Foydalanuvchilar"

    def ready(self) -> None:
        from . import signals

        # Har bir `migrate`dan keyin rollar jadvali bazaga qo'llanadi (roles.py).
        post_migrate.connect(
            signals.sync_after_migrate, sender=self, dispatch_uid="users.sync_role_groups"
        )
