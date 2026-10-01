import os
from typing import Any

from celery import Celery
from celery.signals import after_setup_logger

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("sifatedu")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@after_setup_logger.connect
def count_errors(logger: Any, **_kwargs: Any) -> None:
    """Celery root logger'ni o'zi sozlaydi: xato hisoblagichi worker'larda ham ishlashi uchun."""
    from apps.stats.errors import ErrorCounter

    if not any(isinstance(handler, ErrorCounter) for handler in logger.handlers):
        logger.addHandler(ErrorCounter())
