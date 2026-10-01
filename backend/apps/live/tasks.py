from celery import shared_task

from apps.learning.models import StudyGroup

from . import services


@shared_task
def generate_live_lessons() -> str:
    """Har kecha: haftalik jadvaldan 14 kun oldinga yetishmagan darslar."""
    groups = (
        StudyGroup.objects.exclude(status=StudyGroup.Status.FINISHED)
        .filter(slots__isnull=False)
        .distinct()
    )
    return str(sum(services.generate(group) for group in groups))


@shared_task
def remind_live_lessons() -> str:
    """Har 5 daqiqa: eslatmalar va darsda bo'lmaganlarga xabar."""
    return str(services.remind())
