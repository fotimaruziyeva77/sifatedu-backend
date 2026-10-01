"""Kunlik hisobot Telegram'da: direktor va adminlarga (Telegram'i ulangan bo'lsa) va guruhga."""

import logging
from html import escape

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.notifications import telegram
from apps.notifications.texts import day_month
from apps.users.models import SocialAccount, User
from apps.users.roles import Role

from . import metrics

logger = logging.getLogger(__name__)

MAX_PROBLEMS = 8


def som(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " so'm"


def render(p: metrics.Period) -> str:
    now, before = metrics.summary(p), metrics.summary(p.previous)
    title = f"{day_month(timezone.localdate(p.start), 'uz')}"
    lines = [
        f"📊 <b>Sifat Edu — {escape(title)}</b>",
        "",
        f"👤 Ro'yxatdan o'tdi: <b>{now.registered}</b> ({p.previous_label} {before.registered})",
        f"🎓 Kurs tanladi: <b>{now.chose_course}</b> · to'ladi: <b>{now.paid}</b>"
        f" — {som(now.revenue)}",
        f"📝 Arizalar: <b>{now.leads}</b> (AI orqali: {now.leads_ai})",
        f"🤖 AI suhbatlar: <b>{now.conversations}</b> · ${now.ai_cost:.2f}",
        "",
    ]
    found = metrics.problems(p)
    if found:
        lines.append("⚠️ <b>Muammolar</b>")
        lines.extend(
            f"• {escape(problem.title)} — {problem.count}" for problem in found[:MAX_PROBLEMS]
        )
    else:
        lines.append("✅ Muammo yo'q")
    lines.extend(["", f"Batafsil: {settings.APP_URL.rstrip('/')}/admin/"])
    return "\n".join(lines)


def recipients() -> list[SocialAccount]:
    """Direktor va adminlar (superuser ham) — Telegram'i ulangan va xabarlar yoqilgan."""
    leaders = User.objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=[Role.DIRECTOR, Role.ADMIN])
    )
    return list(
        SocialAccount.objects.filter(
            provider=SocialAccount.Provider.TELEGRAM,
            user__in=leaders,
            notify=True,
            blocked_at__isnull=True,
        ).distinct()
    )


def send_daily_report() -> int:
    """Bugungi hisobotni yuboradi. Qaytadi: nechta chatga yetdi."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return 0
    message = render(metrics.period("today"))
    accounts = {account.uid: account for account in recipients()}
    chats: list[str] = list(accounts)
    if settings.TELEGRAM_REPORTS_CHAT_ID:
        chats.append(str(settings.TELEGRAM_REPORTS_CHAT_ID))
    sent = 0
    for chat in dict.fromkeys(chats):
        try:
            telegram.send_message(chat, message)
        except telegram.TelegramError as exc:
            account = accounts.get(chat)
            if exc.unreachable and account is not None:
                SocialAccount.objects.filter(pk=account.pk).update(blocked_at=timezone.now())
            logger.warning("Kunlik hisobot yuborilmadi (%s): %s", chat, exc)
        except (OSError, telegram.TelegramNotConfiguredError) as exc:
            logger.warning("Kunlik hisobot yuborilmadi (%s): %s", chat, exc)
        else:
            sent += 1
    return sent
