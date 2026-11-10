"""AI xarajati: bugungi va shu oydagi sarf, budjet chegarasi va ogohlantirishlar."""

from datetime import datetime, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from apps.notifications.alerts import alert
from apps.tenancy.access import current_center

from .models import AssistantSettings, Message

WARN_SHARE = Decimal("0.8")
# Qo'llanmadan AI test: tokenlar alohida hisoblanmaydi, bittasining taxminiy narxi.
AI_TEST_COST = Decimal("0.05")


def day_start(now: datetime | None = None) -> datetime:
    local = timezone.localtime(now or timezone.now())
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def month_start(now: datetime | None = None) -> datetime:
    return day_start(now).replace(day=1)


def spent_since(moment: datetime) -> Decimal:
    from apps.quizzes.models import QuizDraft

    total = Message.objects.filter(created_at__gte=moment).aggregate(total=Sum("cost_usd"))["total"]
    return (total or Decimal(0)) + QuizDraft.objects.filter(created_at__gte=moment).count() * (
        AI_TEST_COST
    )


def monthly_limit(config: AssistantSettings) -> Decimal:
    """Markaz qo'ygan budjet tarif chegarasidan oshmaydi: kalit va xarajat platformaniki."""
    center = current_center()
    cap = center.ai_limit if center else None
    return config.monthly_budget_usd if cap is None else min(config.monthly_budget_usd, cap)


def within_budget(config: AssistantSettings) -> bool:
    """Gemini'ni chaqirish mumkinmi. Budjet 0 bo'lsa — AI to'xtatilgan."""
    monthly = monthly_limit(config)
    if config.daily_budget_usd <= 0 or monthly <= 0:
        return False
    if spent_since(day_start()) >= config.daily_budget_usd:
        _warn_once(
            f"day:{day_start():%Y-%m-%d}", "Kunlik AI budjeti tugadi: oddiy rejim ishlayapti."
        )
        return False
    if spent_since(month_start()) >= monthly:
        _warn_once(
            f"month:{month_start():%Y-%m}", "Oylik AI budjeti tugadi: oddiy rejim ishlayapti."
        )
        return False
    return True


def check_warning(config: AssistantSettings) -> None:
    """Oylik budjetning 80 foiziga yetganda bir marta ogohlantiradi."""
    spent = spent_since(month_start())
    monthly = monthly_limit(config)
    if monthly > 0 and spent >= monthly * WARN_SHARE:
        _warn_once(
            f"month80:{month_start():%Y-%m}",
            f"AI xarajati oylik budjetning 80 foiziga yetdi: ${spent:.2f} / ${monthly:.2f}.",
        )


def _warn_once(key: str, text: str) -> None:
    # alert() o'zi 10 daqiqalik cheklovga ega; bu yerda — davr (kun/oy) davomida bir marta.
    if cache.add(f"assistant:budget:{key}", 1, timeout=int(timedelta(days=32).total_seconds())):
        alert(f"assistant:{key.split(':', 1)[0]}", text)
