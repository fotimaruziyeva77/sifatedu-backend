from celery import shared_task

from . import services


@shared_task
def open_day() -> int:
    """07:00: guruhlarga bugungi kunlik test."""
    return services.open_day()


@shared_task
def remind() -> int:
    """20:00: hali ishlamaganlarga — test 23:00 da yopiladi."""
    return services.remind()


@shared_task
def close_day() -> int:
    """23:00: vaqti tugagan testlar yopiladi, tugatilmaganlari hisoblanadi."""
    return services.close_day()
