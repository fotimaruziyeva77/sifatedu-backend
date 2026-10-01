"""AI xarajati: bugungi va shu oydagi sarf, budjet chegarasi va ogohlantirishlar."""

from datetime import datetime, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from apps.notifications.alerts import alert

from .models import AssistantSettings, Message

WARN_SHARE = Decimal("0.8")


def day_start(now: datetime | None = None) -> datetime:
    local = timezone.localtime(now or timezone.now())
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def month_start(now: datetime | None = None) -> datetime:
    return day_start(now).replace(day=1)


def spent_since(moment: datetime) -> Decimal:
    total = Message.objects.filter(created_at__gte=moment).aggregate(total=Sum("cost_usd"))["total"]
    return total or Decimal(0)


def within_budget(config: AssistantSettings) -> bool:
    """Claude'ni chaqirish mumkinmi. Budjet 0 bo'lsa — AI to'xtatilgan."""
    if config.daily_budget_usd <= 0 or config.monthly_budget_usd <= 0:
        return False
    if spent_since(day_start()) >= config.daily_budget_usd:
        _warn_once(
            f"day:{day_start():%Y-%m-%d}", "Kunlik AI budjeti tugadi: oddiy rejim ishlayapti."
        )
        return False
    if spent_since(month_start()) >= config.monthly_budget_usd:
        _warn_once(
            f"month:{month_start():%Y-%m}", "Oylik AI budjeti tugadi: oddiy rejim ishlayapti."
        )
        return False
    return True


def check_warning(config: AssistantSettings) -> None:
    """Oylik budjetning 80 foiziga yetganda bir marta ogohlantiradi."""
    spent = spent_since(month_start())
    if config.monthly_budget_usd > 0 and spent >= config.monthly_budget_usd * WARN_SHARE:
        _warn_once(
            f"month80:{month_start():%Y-%m}",
            f"AI xarajati oylik budjetning 80 foiziga yetdi: ${spent:.2f} / "
            f"${config.monthly_budget_usd:.2f}.",
        )


def _warn_once(key: str, text: str) -> None:
    # alert() o'zi 10 daqiqalik cheklovga ega; bu yerda — davr (kun/oy) davomida bir marta.
    if cache.add(f"assistant:budget:{key}", 1, timeout=int(timedelta(days=32).total_seconds())):
        alert(f"assistant:{key.split(':', 1)[0]}", text)
