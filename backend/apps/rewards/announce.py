"""Botdagi xabarlar: ertalabki topshiriqlar va haftalik g'oliblar (kanalga, admin yoqsa)."""

import logging

from django.utils import timezone

from apps.users.models import SocialAccount

from . import rating, services
from .models import DailyTask

logger = logging.getLogger(__name__)


def morning() -> int:
    """Bugun topshirig'i bor, Telegram'i ulangan va botni bloklamagan o'quvchilarga."""
    from apps.bot import today
    from apps.bot.models import BotChat

    day = timezone.localdate()
    user_ids = set(DailyTask.objects.filter(day=day).values_list("user_id", flat=True))
    accounts = SocialAccount.objects.filter(
        user_id__in=user_ids,
        provider=SocialAccount.Provider.TELEGRAM,
        blocked_at__isnull=True,
    ).select_related("user")
    chats = {
        str(chat.chat_id): chat
        for chat in BotChat.objects.filter(
            chat_id__in=[int(account.uid) for account in accounts if account.uid.isdigit()],
            blocked_at__isnull=True,
        )
    }
    sent = 0
    for account in accounts:
        chat = chats.get(account.uid)
        if chat is None or not chat.language:
            continue
        sent += today.morning(chat, account.user)
    return sent


def winners() -> int:
    """Dushanba: o'tgan haftaning eng faol 3 o'quvchisi — birinchi faol majburiy kanalga."""
    if not services.settings().announce_winners:
        return 0
    from apps.bot.models import RequiredChannel
    from apps.bot.send import escape
    from apps.bot.texts import t
    from apps.notifications import telegram

    channel = RequiredChannel.objects.filter(is_active=True).order_by("order", "pk").first()
    found = rating.weekly_winners()
    if channel is None or not found:
        return 0
    medals = ["🥇", "🥈", "🥉"]
    lines = [t("uz", "winners_title")]
    for index, (person, points) in enumerate(found):
        lines.append(f"{medals[index]} {escape(rating.short_name(person))} — {points} XP")
    lines.append(t("uz", "winners_footer"))
    try:
        telegram.send_message(channel.chat, "\n".join(lines))
    except (OSError, RuntimeError, telegram.TelegramNotConfiguredError) as exc:
        logger.warning("Haftalik g'oliblar kanalga yuborilmadi: %s", exc)
        return 0
    return len(found)
