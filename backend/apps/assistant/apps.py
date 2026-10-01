from django.apps import AppConfig


class AssistantConfig(AppConfig):
    name = "apps.assistant"
    verbose_name = "AI yordamchi"

    def ready(self) -> None:
        from . import signals  # noqa: F401
