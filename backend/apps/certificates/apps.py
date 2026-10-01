from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    name = "apps.certificates"
    verbose_name = "Sertifikatlar"

    def ready(self) -> None:
        from . import receivers  # noqa: F401 - hodisalarni tinglash
