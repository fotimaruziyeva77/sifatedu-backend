from django.apps import AppConfig


class ContentConfig(AppConfig):
    name = "apps.content"
    verbose_name = "Sayt kontenti"

    def ready(self) -> None:
        from . import signals  # noqa: F401
