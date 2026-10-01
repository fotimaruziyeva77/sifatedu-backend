from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = "apps.catalog"
    verbose_name = "Katalog"

    def ready(self) -> None:
        from . import signals  # noqa: F401 - signal qabul qiluvchilarni ro'yxatga olish
