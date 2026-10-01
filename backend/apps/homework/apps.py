from django.apps import AppConfig


class HomeworkConfig(AppConfig):
    name = "apps.homework"
    verbose_name = "Uy vazifalari"

    def ready(self) -> None:
        from . import signals  # noqa: F401 - fayllarni storage'dan o'chirish
