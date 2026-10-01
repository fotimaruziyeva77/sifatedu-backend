from django.apps import AppConfig


class RewardsConfig(AppConfig):
    name = "apps.rewards"
    verbose_name = "XP va coin"

    def ready(self) -> None:
        from . import receivers  # noqa: F401 — hodisa tinglovchilari
