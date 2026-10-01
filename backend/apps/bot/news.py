"""Yangiliklar botdagi hammaga — ro'yxatdan o'tmaganlarga ham (admin: "Botdagi hammaga ham").

Ro'yxatdan o'tgan va Telegram'i ulangan o'quvchi xabarni odatdagidek (kabinet + Telegram) oladi;
bu yerda — qolgan bot foydalanuvchilari. Har bir odamga bir marta: vazifa qayta urinsa ham,
yuborilganlar o'tkazib yuboriladi. Har xabar ostida "Yangiliklarni o'chirish" tugmasi.
"""

from collections.abc import Iterable
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.db.models import F

from apps.notifications import telegram
from apps.notifications.models import Broadcast, Delivery
from apps.notifications.services import absolute_link, chunks
from apps.users.models import SocialAccount

from .models import BotChat
from .send import button, escape, inline, link, mark_blocked
from .texts import t

TELEGRAM = SocialAccount.Provider.TELEGRAM
SENT_TTL = 7 * 24 * 60 * 60


def _uids(values: Iterable[str]) -> set[int]:
    return {int(value) for value in values if value.isdigit()}


def subscribers(skip: set[int]) -> list[int]:
    """Yangiliklarni o'chirmagan va botni bloklamaganlar (`skip`dagilardan tashqari)."""
    chats = BotChat.objects.filter(news=True, blocked_at__isnull=True).values_list(
        "chat_id", flat=True
    )
    return [chat_id for chat_id in chats if chat_id not in skip]


def muted() -> set[int]:
    """Saytda Telegram xabarlarini o'chirgan o'quvchilar — ularga botda ham yozilmaydi."""
    return _uids(
        SocialAccount.objects.filter(provider=TELEGRAM, notify=False).values_list("uid", flat=True)
    )


def count(reachable_uids: Iterable[str]) -> int:
    """Tasdiqlash oynasi uchun: xabarni bot orqali qo'shimcha oladiganlar soni."""
    return len(subscribers(_uids(reachable_uids) | muted()))


def audience(broadcast: Broadcast) -> list[int]:
    """Xabarni Telegram orqali allaqachon olayotgan o'quvchilarsiz bot foydalanuvchilari."""
    reached = SocialAccount.objects.filter(
        provider=TELEGRAM,
        user__notifications__broadcast=broadcast,
        user__notifications__telegram__in=[Delivery.QUEUED, Delivery.SENT],
    ).values_list("uid", flat=True)
    return subscribers(_uids(reached) | muted())


def queue(broadcast: Broadcast) -> int:
    """Bot foydalanuvchilariga yuborishni navbatga qo'yadi (tranzaksiyadan keyin)."""
    chat_ids = audience(broadcast)
    Broadcast.objects.filter(pk=broadcast.pk).update(bot_recipients=len(chat_ids))
    from .tasks import deliver_news

    broadcast_id = broadcast.pk

    def enqueue() -> None:
        for batch in chunks(chat_ids):
            deliver_news.delay(broadcast_id, batch)

    transaction.on_commit(enqueue)
    return len(chat_ids)


def message(broadcast: Broadcast, locale: str) -> tuple[str, dict[str, Any] | None]:
    text = f"<b>{escape(broadcast.title)}</b>"
    if broadcast.body:
        text += f"\n\n{escape(broadcast.body)}"
    rows = []
    if broadcast.link:
        rows.append([link(t(locale, "btn_open"), absolute_link(broadcast.link, locale))])
    rows.append([button(t(locale, "btn_news_off"), "mute")])
    return inline(text, rows)


def deliver(broadcast_id: int, chat_ids: list[int]) -> tuple[int, int]:
    """Bir to'plam. Qaytadi: (yetdi, yetmadi). Telegram 429 va tarmoq xatosi tashqariga chiqadi —
    vazifa qayta urinadi (shu odam "yuborilmagan" deb qoladi)."""
    broadcast = Broadcast.objects.filter(pk=broadcast_id).first()
    if broadcast is None:
        return 0, 0
    chats = {chat.chat_id: chat for chat in BotChat.objects.filter(chat_id__in=chat_ids)}
    image = broadcast.image.name if broadcast.image else ""
    sent = failed = 0
    try:
        for chat_id in chat_ids:
            chat = chats.get(chat_id)
            if chat is None or chat.blocked_at is not None or not chat.news:
                continue
            key = f"bot:news:{broadcast_id}:{chat_id}"
            if not cache.add(key, 1, SENT_TTL):
                continue
            text, markup = message(broadcast, chat.language or "uz")
            try:
                telegram.send_rich(chat_id, text, image=image, reply_markup=markup)
            except telegram.TelegramError as exc:
                if exc.code == 429:
                    cache.delete(key)
                    raise
                failed += 1
                if exc.unreachable:
                    mark_blocked(chat_id)
            except OSError:
                cache.delete(key)
                raise
            except telegram.TelegramNotConfiguredError:
                failed += 1
            else:
                sent += 1
    finally:
        if sent or failed:
            Broadcast.objects.filter(pk=broadcast_id).update(
                bot_sent=F("bot_sent") + sent, bot_failed=F("bot_failed") + failed
            )
    return sent, failed
