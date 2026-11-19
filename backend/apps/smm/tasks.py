"""SMM agent vazifalari. Har bir markaz sxemasida ishlaydi, lekin sozlamada yoqilmagan bo'lsa —
hech narsa qilmaydi. AI chaqiruvlari `ai` navbatida (`worker-ai`)."""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.tenancy.db import connection

from . import ai, services
from .models import Post, SmmSettings

logger = logging.getLogger(__name__)

# `prepare` vazifasi o'ldirilsa (vaqt chegarasi, xotira, deploy), post «tayyorlanmoqda»da
# qolib ketmasin: shuncha vaqtdan keyin qayta navbatga qo'yiladi.
STUCK_AFTER = timedelta(minutes=10)
MAX_ATTEMPTS = 3
STUCK_PUBLISHING_AFTER = timedelta(minutes=15)
PLAN_LOCK_SECONDS = 300
RETRY_AFTER_SECONDS = 300


def active() -> bool:
    return SmmSettings.load().enabled and ai.ready()


@shared_task(
    acks_late=False,
    soft_time_limit=340,
    time_limit=360,
    autoretry_for=(ai.AiError,),
    max_retries=3,
    retry_backoff=600,
    retry_jitter=False,
)
def plan_week(current: bool = False) -> int:
    """Yakshanba: keyingi hafta rejasi; `current` — shu haftaning qolgani (agent yoqilganda).
    AI xato qilsa — 10, 20, 40 daqiqadan keyin yana. Bir vaqtda ikkita reja tuzilmaydi."""
    if not active():
        return 0
    lock = f"smm-plan:{connection.schema_name}"
    if not cache.add(lock, 1, timeout=PLAN_LOCK_SECONDS):
        return 0
    try:
        start = services.this_week(timezone.localdate()) if current else None
        created = services.plan_week(start)
    finally:
        cache.delete(lock)
    if current:
        # Yaqin postlar soat boshini kutmasin.
        soon = timezone.now() + services.LEAD
        for post in created:
            if post.publish_at <= soon:
                prepare.delay(post.pk)
    return len(created)


def recover_stuck_publishing(now: datetime) -> None:
    """`publish` o'ldirilsa (deploy, xotira): post xato bo'ladi — kanal va Instagram tekshiriladi.
    Chiqib bo'lgan joylar yozilgan, qayta urinishda faqat qolgani yuboriladi."""
    Post.objects.filter(
        status=Post.Status.PUBLISHING, updated_at__lt=now - STUCK_PUBLISHING_AFTER
    ).update(
        status=Post.Status.FAILED,
        error="Chiqarish to'xtab qoldi — kanal va Instagram'ni tekshiring.",
    )


def recover_stuck(now: datetime) -> None:
    stuck = Post.objects.filter(status=Post.Status.MAKING, updated_at__lt=now - STUCK_AFTER)
    for post in stuck:
        if post.attempts + 1 >= MAX_ATTEMPTS:
            post.status, post.error = Post.Status.FAILED, "Tayyorlash to'xtab qoldi."
        else:
            post.status = Post.Status.PLANNED
        post.attempts += 1
        post.save(update_fields=["status", "error", "attempts", "updated_at"])


@shared_task
def prepare_due() -> int:
    """Chiqishiga 30 soatdan kam qolgan rejadagi postlar tayyorlanadi. Vaqti o'tib ketganlari
    (agent o'chiq turgan kunlar) tayyorlanmaydi — bekor bo'ladi."""
    if not active():
        return 0
    now = timezone.now()
    recover_stuck(now)
    week_end = services.slot_time(services.week_start(timezone.localdate(now)), Post.Kind.POST, 0)
    if not Post.objects.filter(publish_at__gt=now, publish_at__lt=week_end).exists():
        # Shu haftada oldinda hech narsa yo'q (agent endigina yoqildi): qolgani rejalanadi.
        plan_week.delay(current=True)
    Post.objects.filter(status=Post.Status.PLANNED, publish_at__lt=now - services.GRACE).update(
        status=Post.Status.REJECTED, error="Vaqti o'tib ketdi."
    )
    due = list(
        Post.objects.filter(
            status=Post.Status.PLANNED, publish_at__lte=now + services.LEAD
        ).values_list("pk", flat=True)
    )
    for pk in due:
        prepare.delay(pk)
    return len(due)


@shared_task(acks_late=False, soft_time_limit=340, time_limit=360)
def prepare(post_id: int) -> None:
    with transaction.atomic():
        claimed = Post.objects.filter(pk=post_id, status=Post.Status.PLANNED).update(
            status=Post.Status.MAKING, updated_at=timezone.now()
        )
    if not claimed:
        return
    post = Post.objects.get(pk=post_id)
    try:
        services.make(post)
    except ai.AiError as exc:
        # Gemini band yoki sekin (504, 503): 5 daqiqadan keyin yana, jami 3 marta.
        logger.warning("SMM post tayyorlanmadi (%s): %s", post_id, exc)
        retry = post.attempts + 1 < MAX_ATTEMPTS
        Post.objects.filter(pk=post_id, status=Post.Status.MAKING).update(
            status=Post.Status.PLANNED if retry else Post.Status.FAILED,
            attempts=post.attempts + 1,
            error=str(exc)[:500],
        )
        if retry:
            prepare.apply_async((post_id,), countdown=RETRY_AFTER_SECONDS)
    except Exception as exc:
        logger.exception("SMM post tayyorlanmadi (%s)", post_id)
        Post.objects.filter(pk=post_id, status=Post.Status.MAKING).update(
            status=Post.Status.FAILED, error=str(exc)[:500]
        )


@shared_task
def publish_due() -> int:
    """Vaqti kelgan tasdiqlangan postlar kanalga; tasdiqlanmaganlari bekor bo'ladi. Juda kech
    qolganlari (server ishlamagan soatlar) chiqmaydi — eskirgan post kanalga tushmasin."""
    if not SmmSettings.load().enabled:
        return 0
    now = timezone.now()
    recover_stuck_publishing(now)
    services.expire_unanswered(now)
    approved = Post.objects.filter(status=Post.Status.APPROVED).exclude(kind=Post.Kind.SCRIPT)
    approved.filter(publish_at__lt=now - services.LATE_PUBLISH).update(
        status=Post.Status.REJECTED, error="Vaqtida chiqarilmadi."
    )
    due = list(approved.filter(publish_at__lte=now).values_list("pk", flat=True))
    for pk in due:
        publish.delay(pk)
    return len(due)


# Instagram konteynerini kutish (8 × 5 s har biri) + Telegram albomi.
@shared_task(acks_late=False, soft_time_limit=280, time_limit=300)
def publish(post_id: int) -> None:
    """Avval post «chiqarilmoqda» deb belgilanadi (tranzaksiya yopiladi), keyin Telegram.
    Shunda ikkinchi vazifa uni olmaydi va qisman yuborilgan xabarlar yozib boriladi."""
    with transaction.atomic():
        claimed = (
            Post.objects.filter(pk=post_id, status=Post.Status.APPROVED)
            .exclude(kind=Post.Kind.SCRIPT)
            .update(status=Post.Status.PUBLISHING, updated_at=timezone.now())
        )
    if not claimed:
        return
    post = Post.objects.get(pk=post_id)
    try:
        services.publish(post)
    except Exception as exc:
        logger.exception("SMM post kanalga chiqmadi (%s)", post_id)
        post.refresh_from_db(fields=["channel_messages"])
        note = "Kanalga qisman chiqdi — kanalni tekshiring. " if post.channel_messages else ""
        Post.objects.filter(pk=post_id).update(
            status=Post.Status.FAILED, error=f"{note}{exc}"[:500]
        )


@shared_task
def refresh_instagram() -> bool:
    """Har dushanba: Instagram tokeni (60 kunlik) yangilanadi."""
    if not SmmSettings.load().ig_token:
        return False
    return services.refresh_instagram()
