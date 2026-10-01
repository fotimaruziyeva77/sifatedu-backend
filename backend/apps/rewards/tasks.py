from celery import shared_task

from . import announce, daily


@shared_task
def daily_tasks() -> str:
    """09:00: bugungi topshiriqlar va botdagi xabar."""
    created = daily.generate()
    sent = announce.morning()
    return f"{created} / {sent}"


@shared_task
def close_day() -> str:
    """00:10: kechagi topshiriqlari bajarilmaganlarga shtraf."""
    return f"{daily.close()}"


@shared_task
def weekly_winners() -> str:
    """Dushanba 10:00: o'tgan haftaning g'oliblari (admin'da yoqilgan bo'lsa)."""
    return f"{announce.winners()}"
