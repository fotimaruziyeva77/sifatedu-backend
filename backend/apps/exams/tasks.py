from celery import shared_task

from . import services


@shared_task
def create_exam_drafts() -> str:
    """Har oyning 20-kuni: imtihon yoqilgan kurslarga qoralama va o'qituvchilarga eslatma."""
    return f"{services.create_drafts()}"


@shared_task
def exam_tick() -> str:
    """Har 5 daqiqada: ochilish xabarlari, vaqti tugagan testlar, yakuniy natijalar."""
    opened = services.announce_open()
    closed = services.close_overdue()
    final = services.finalize()
    return f"{opened}/{closed}/{final}"
