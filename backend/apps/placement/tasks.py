from celery import shared_task

from . import services


@shared_task
def close_expired() -> int:
    """Har 5 daqiqada: vaqti tugagan, botda yakunlanmagan daraja testlari."""
    return services.close_expired()


@shared_task
def coupon_reminders() -> int:
    """Soatda bir: daraja testi kuponi eslatmalari (24 soatdan keyin va tugashiga 12 soat
    qolganda)."""
    return services.coupon_reminders()
