"""Xabar yuborish: kabinetga yozish, kanal tanlash, auditoriya va yetkazish.

Kanal qoidalari:
* kabinet — har doim;
* Telegram — foydalanuvchi ulagan, o'chirmagan va botni bloklamagan bo'lsa;
* SMS — faqat SMS matni berilgan bo'lsa va Telegram ishlamasa (pullik zaxira);
* aksiya (`promo`) — Telegram va SMS orqali faqat rozilik berganlarga.
"""

import logging
import math
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from html import escape
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.learning.models import Enrollment
from apps.users.models import SocialAccount, User

from . import telegram
from .models import Broadcast, Delivery, Notification
from .sms import SmsNotConfiguredError, send_sms
from .texts import locale_of, text

logger = logging.getLogger(__name__)

TELEGRAM = SocialAccount.Provider.TELEGRAM
BATCH_SIZE = 25
TELEGRAM_TEXT_LIMIT = 4096
# Aksiya va eslatmalar tunda yuborilmaydi (TZ 4.12).
QUIET_FROM = time(22, 0)
QUIET_UNTIL = time(9, 0)


def telegram_accounts(user_ids: Iterable[int]) -> dict[int, SocialAccount]:
    accounts = SocialAccount.objects.filter(provider=TELEGRAM, user_id__in=list(user_ids))
    return {account.user_id: account for account in accounts}


def can_message(account: SocialAccount | None) -> bool:
    """Bot bu odamga yoza oladimi."""
    return bool(
        settings.TELEGRAM_BOT_TOKEN
        and account is not None
        and account.notify
        and account.blocked_at is None
    )


def build(
    user: User,
    kind: str,
    *,
    title: str,
    body: str = "",
    link: str = "",
    sms_text: str = "",
    promo: bool = False,
    account: SocialAccount | None = None,
    broadcast: Broadcast | None = None,
    dedupe_key: str | None = None,
    image: str = "",
    quiz_id: int | None = None,
) -> Notification:
    """Saqlanmagan xabar: qaysi kanal ishlatilishi shu yerda hal qilinadi."""
    consent = not promo or user.marketing_consent_at is not None
    via_telegram = consent and can_message(account)
    sms_allowed = sms_text.strip() if consent else ""
    return Notification(
        user=user,
        kind=kind,
        broadcast=broadcast,
        title=title[:120],
        body=body,
        link=link,
        telegram=Delivery.QUEUED if via_telegram else "",
        sms=Delivery.QUEUED if sms_allowed and not via_telegram else "",
        sms_text=sms_allowed[:300],
        dedupe_key=dedupe_key,
        image=image,
        quiz_id=quiz_id,
    )


def notify(
    user: User,
    kind: str,
    *,
    title: str,
    body: str = "",
    link: str = "",
    sms_text: str = "",
    telegram_allowed: bool = True,
    dedupe_key: str | None = None,
    image: str = "",
    quiz_id: int | None = None,
) -> Notification | None:
    """Bitta foydalanuvchiga xabar. `dedupe_key` bilan xabar allaqachon bo'lsa — None.
    `quiz_id` — Telegram'da "Testni boshlash" tugmasi (test botda ochiladi)."""
    if dedupe_key and Notification.objects.filter(dedupe_key=dedupe_key).exists():
        return None
    account = telegram_accounts([user.pk]).get(user.pk) if telegram_allowed else None
    notification = build(
        user,
        kind,
        title=title,
        body=body,
        link=link,
        sms_text=sms_text,
        account=account,
        dedupe_key=dedupe_key,
        image=image,
        quiz_id=quiz_id,
    )
    try:
        with transaction.atomic():
            notification.save()
    except IntegrityError:
        # Parallel ishga tushgan eslatma: ikkinchisi yozilmaydi.
        return None
    dispatch([notification.pk] if needs_delivery(notification) else [])
    return notification


def needs_delivery(notification: Notification) -> bool:
    return Delivery.QUEUED in (notification.telegram, notification.sms)


def chunks(items: Sequence[int], size: int = BATCH_SIZE) -> Iterator[list[int]]:
    for start in range(0, len(items), size):
        yield list(items[start : start + size])


def dispatch(notification_ids: Sequence[int]) -> None:
    """Tashqi kanallarni navbatga qo'yadi — tranzaksiya yopilgandan keyin."""
    if not notification_ids:
        return
    from .tasks import deliver

    ids = list(notification_ids)

    def enqueue() -> None:
        for batch in chunks(ids):
            deliver.delay(batch)

    transaction.on_commit(enqueue)


# --- Yetkazish ---


def absolute_link(link: str, locale: str) -> str:
    if link.startswith("/"):
        return f"{settings.APP_URL.rstrip('/')}/{locale}{link}"
    return link


def telegram_message(notification: Notification) -> tuple[str, dict[str, Any] | None]:
    """Telegram HTML matni va (havola bo'lsa) tugma."""
    locale = locale_of(notification.user.locale)
    message = f"<b>{escape(notification.title, quote=False)}</b>"
    if notification.body:
        message += f"\n\n{escape(notification.body, quote=False)}"
    rows: list[list[dict[str, Any]]] = []
    if notification.quiz_id:
        # Test botning o'zida ochiladi (bot routeri `qs:<id>` ni tushunadi).
        rows.append(
            [{"text": text(locale, "start_quiz"), "callback_data": f"qs:{notification.quiz_id}"}]
        )
    elif notification.kind == Notification.Kind.DAILY_TEST:
        # Kunlik test ham botda: `dq` — bugungi test (shartlar yoki davomi).
        rows.append([{"text": text(locale, "start_daily_test"), "callback_data": "dq"}])
    if notification.link:
        url = absolute_link(notification.link, locale)
        if url.startswith("https://"):
            rows.append([{"text": text(locale, "open"), "url": url}])
        else:
            # Local muhit: Telegram tugmada http/localhost havolani qabul qilmaydi.
            message += f"\n\n{escape(url, quote=False)}"
    markup = {"inline_keyboard": rows} if rows else None
    return message[:TELEGRAM_TEXT_LIMIT], markup


def deliver_one(notification: Notification, account: SocialAccount | None) -> None:
    """Bitta xabarni Telegram va/yoki SMS orqali yuboradi va holatini saqlaydi.

    Telegram 429 (limit) va tarmoq xatolari tashqariga chiqadi — vazifa qayta uriniladi;
    allaqachon yuborilganlar saqlangani uchun qayta yuborilmaydi.
    """
    if notification.telegram == Delivery.QUEUED:
        if account is None or not can_message(account):
            notification.telegram = Delivery.FAILED
            notification.error = "Telegram ulanmagan yoki o'chirilgan"
        else:
            message, markup = telegram_message(notification)
            try:
                telegram.send_rich(
                    account.uid, message, image=notification.image, reply_markup=markup
                )
            except telegram.TelegramError as exc:
                if exc.code == 429:
                    raise
                notification.telegram = Delivery.FAILED
                notification.error = exc.description[:300]
                if exc.unreachable:
                    mark_blocked(account)
            except telegram.TelegramNotConfiguredError:
                notification.telegram = Delivery.FAILED
                notification.error = "Telegram sozlanmagan"
            else:
                notification.telegram = Delivery.SENT
        if notification.telegram == Delivery.FAILED and notification.sms_text:
            notification.sms = Delivery.QUEUED
        notification.save(update_fields=["telegram", "sms", "error"])

    if notification.sms == Delivery.QUEUED:
        try:
            send_sms(notification.user.phone, notification.sms_text)
        except SmsNotConfiguredError:
            notification.sms = Delivery.FAILED
            notification.error = "SMS sozlanmagan"
        except RuntimeError as exc:
            notification.sms = Delivery.FAILED
            notification.error = str(exc)[:300]
        else:
            notification.sms = Delivery.SENT
        notification.save(update_fields=["sms", "error"])


def mark_blocked(account: SocialAccount) -> None:
    account.blocked_at = timezone.now()
    SocialAccount.objects.filter(pk=account.pk).update(blocked_at=account.blocked_at)


# --- Ommaviy xabar ---


def day_start(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time.min))


def recipients(broadcast: Broadcast) -> QuerySet[User]:
    """Xabar kimlarga boradi: faol o'quvchilar (xodimlar emas) filtrlar bo'yicha."""
    users = User.objects.filter(is_active=True, is_staff=False)
    if broadcast.audience != Broadcast.Audience.ALL:
        users = users.filter(audience=broadcast.audience)
    active = Enrollment.objects.filter(status=Enrollment.Status.ACTIVE)
    course_ids = list(broadcast.courses.values_list("pk", flat=True)) if broadcast.pk else []
    group_ids = list(broadcast.groups.values_list("pk", flat=True)) if broadcast.pk else []
    if course_ids or group_ids:
        users = users.filter(
            pk__in=active.filter(Q(course_id__in=course_ids) | Q(group_id__in=group_ids)).values(
                "user_id"
            )
        )
    if broadcast.without_course:
        users = users.exclude(pk__in=active.values("user_id"))
    if broadcast.joined_from:
        users = users.filter(date_joined__gte=day_start(broadcast.joined_from))
    if broadcast.joined_to:
        users = users.filter(date_joined__lt=day_start(broadcast.joined_to + timedelta(days=1)))
    return users


def sms_parts(message: str) -> int:
    """SMS bo'laklari: lotin — 160 (bo'lakda 153), kirill — 70 (bo'lakda 67) belgi."""
    if not message:
        return 0
    unicode = any(ord(char) > 127 for char in message)
    single, part = (70, 67) if unicode else (160, 153)
    return 1 if len(message) <= single else math.ceil(len(message) / part)


@dataclass(frozen=True)
class Reach:
    """Tasdiqlash oynasi uchun: xabar kimga qaysi kanal orqali yetadi. `bot` — "Botdagi
    hammaga": qo'shimcha ravishda bot orqali oladiganlar (ro'yxatdan o'tmaganlar ham)."""

    total: int
    telegram: int
    sms: int
    sms_cost: int
    bot: int = 0

    @property
    def site_only(self) -> int:
        return self.total - self.telegram - self.sms


def reach(broadcast: Broadcast) -> Reach:
    users = recipients(broadcast)
    total = users.count()
    consenting = (
        users.filter(marketing_consent_at__isnull=False)
        if broadcast.kind == Broadcast.Kind.PROMO
        else users
    )
    reachable = consenting.filter(
        social_accounts__provider=TELEGRAM,
        social_accounts__notify=True,
        social_accounts__blocked_at__isnull=True,
    )
    telegram_count = (
        reachable.count() if broadcast.send_telegram and settings.TELEGRAM_BOT_TOKEN else 0
    )
    sms_count = 0
    if broadcast.send_sms and broadcast.sms_text.strip():
        sms_users = consenting
        if telegram_count:
            sms_users = sms_users.exclude(pk__in=reachable.values("pk"))
        sms_count = sms_users.count()
    cost = sms_count * sms_parts(broadcast.sms_text.strip()) * settings.SMS_PRICE_UZS
    bot_count = 0
    if broadcast.bot_all and broadcast.send_telegram and settings.TELEGRAM_BOT_TOKEN:
        from apps.bot import news

        uids = SocialAccount.objects.filter(provider=TELEGRAM, user__in=reachable).values_list(
            "uid", flat=True
        )
        bot_count = news.count(uids)
    return Reach(total=total, telegram=telegram_count, sms=sms_count, sms_cost=cost, bot=bot_count)


def in_quiet_hours(moment: datetime) -> bool:
    local = timezone.localtime(moment).time()
    return local >= QUIET_FROM or local < QUIET_UNTIL


def next_morning(moment: datetime) -> datetime:
    """Tungi vaqtdan keyingi birinchi 09:00."""
    local = timezone.localtime(moment)
    day = local.date() if local.time() < QUIET_UNTIL else local.date() + timedelta(days=1)
    return timezone.make_aware(datetime.combine(day, QUIET_UNTIL))


def schedule(broadcast: Broadcast, user: User) -> datetime | None:
    """ "Yuborish" bosildi: darhol navbatga qo'yadi yoki (aksiya yoki botdagi hammaga, tunda)
    09:00 ga suradi. Qaytadi: surilgan vaqt yoki None (hozir yuborilmoqda)."""
    now = timezone.now()
    later = (broadcast.kind == Broadcast.Kind.PROMO or broadcast.bot_all) and in_quiet_hours(now)
    broadcast.status = Broadcast.Status.SCHEDULED
    broadcast.scheduled_for = next_morning(now) if later else now
    broadcast.created_by = broadcast.created_by or user
    broadcast.save(update_fields=["status", "scheduled_for", "created_by", "updated_at"])
    if later:
        return broadcast.scheduled_for
    from .tasks import send_broadcast

    transaction.on_commit(lambda: send_broadcast.delay(broadcast.pk))
    return None


def send(broadcast_id: int) -> int:
    """Xabarni qabul qiluvchilarga yozadi va kanallarni navbatga qo'yadi. Qaytadi: soni.

    Holat atomik o'zgaradi: vazifa ikki marta ishga tushsa ham xabar ikki marta ketmaydi.
    """
    now = timezone.now()
    claimed = Broadcast.objects.filter(
        pk=broadcast_id, status=Broadcast.Status.SCHEDULED, scheduled_for__lte=now
    ).update(status=Broadcast.Status.SENT, sent_at=now)
    if not claimed:
        return 0
    broadcast = Broadcast.objects.get(pk=broadcast_id)
    promo = broadcast.kind == Broadcast.Kind.PROMO
    sms_text = broadcast.sms_text if broadcast.send_sms else ""
    image = broadcast.image.name if broadcast.image else ""
    users = list(recipients(broadcast).only("pk", "locale", "phone", "marketing_consent_at"))
    total = 0
    for start in range(0, len(users), 500):
        part = users[start : start + 500]
        accounts = telegram_accounts(user.pk for user in part) if broadcast.send_telegram else {}
        rows = [
            build(
                user,
                Notification.Kind.BROADCAST,
                title=broadcast.title,
                body=broadcast.body,
                link=broadcast.link,
                sms_text=sms_text,
                promo=promo,
                account=accounts.get(user.pk),
                broadcast=broadcast,
                image=image,
            )
            for user in part
        ]
        Notification.objects.bulk_create(rows, ignore_conflicts=True)
        total += len(rows)
    Broadcast.objects.filter(pk=broadcast.pk).update(recipients=total)
    queued = (
        Notification.objects.filter(broadcast=broadcast)
        .filter(Q(telegram=Delivery.QUEUED) | Q(sms=Delivery.QUEUED))
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    dispatch(list(queued))
    if broadcast.bot_all and broadcast.send_telegram:
        from apps.bot import news

        total += news.queue(broadcast)
    logger.info("Xabar #%s: %s kishiga", broadcast.pk, total)
    return total


def send_test(broadcast: Broadcast, user: User) -> Notification | None:
    """ "Menga sinov": xuddi shu matn faqat yuborayotgan xodimga."""
    return notify(
        user,
        Notification.Kind.TEST,
        title=f"[{text(user.locale, 'test')}] {broadcast.title}",
        body=broadcast.body,
        link=broadcast.link,
        sms_text=broadcast.sms_text if broadcast.send_sms else "",
        telegram_allowed=broadcast.send_telegram,
        image=broadcast.image.name if broadcast.image else "",
    )
