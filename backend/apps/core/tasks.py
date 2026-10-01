from celery import shared_task


@shared_task
def ping() -> str:
    """Worker ishlayotganini tekshirish uchun."""
    return "pong"
