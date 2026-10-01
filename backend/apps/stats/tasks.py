from celery import shared_task

from . import report


@shared_task
def send_daily_report() -> str:
    """Har kuni kechqurun (DAILY_REPORT_HOUR) direktor va adminlarga Telegram'da."""
    return f"{report.send_daily_report()}"
