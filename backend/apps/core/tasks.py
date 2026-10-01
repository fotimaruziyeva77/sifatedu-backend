from celery import shared_task

from apps.notifications import alerts

from . import resources

# Disk yoki xotira muammosi bir kunda yo'qolmaydi: eslatma 6 soatda bir.
RESOURCE_ALERT_COOLDOWN = 6 * 60 * 60


@shared_task
def ping() -> str:
    """Worker ishlayotganini tekshirish uchun."""
    return "pong"


@shared_task
def check_server_resources() -> list[str]:
    """Soatda bir: disk yoki xotira chegaradan oshgan bo'lsa — jamoaga Telegram ogohlantirish."""
    found = resources.warnings()
    for kind, text in found:
        alerts.alert(kind, text, cooldown=RESOURCE_ALERT_COOLDOWN)
    return [kind for kind, _text in found]
