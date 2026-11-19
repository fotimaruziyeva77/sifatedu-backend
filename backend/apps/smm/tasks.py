"""SMM agent vazifalari. Har bir markaz sxemasida ishlaydi, lekin sozlamada yoqilmagan bo'lsa —
hech narsa qilmaydi. AI chaqiruvlari `ai` navbatida (`worker-ai`)."""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from . import ai, services
from .models import Post, SmmSettings

logger = logging.getLogger(__name__)

# `prepare` vazifasi o'ldirilsa (vaqt chegarasi, xotira, deploy), post «tayyorlanmoqda»da
# qolib ketmasin: shuncha vaqtdan keyin qayta navbatga qo'yiladi.
STUCK_AFTER = timedelta(minutes=10)
MAX_ATTEMPTS = 3


def active() -> bool:
    return SmmSettings.load().enabled and ai.ready()


@shared_task(
    acks_late=False,
    soft_time_limit=200,
    time_limit=240,
    autoretry_for=(ai.AiError,),
    max_retries=3,
    retry_backoff=600,
    retry_jitter=False,
)
def plan_week() -> int:
    """Yakshanba: keyingi hafta rejasi. AI xato qilsa — 10, 20, 40 daqiqadan keyin yana."""
    if not active():
        return 0
    return len(services.plan_week())


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


@shared_task(acks_late=False, soft_time_limit=200, time_limit=240)
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
    services.expire_unanswered(now)
    approved = Post.objects.filter(status=Post.Status.APPROVED).exclude(kind=Post.Kind.SCRIPT)
    approved.filter(publish_at__lt=now - services.LATE_PUBLISH).update(
        status=Post.Status.REJECTED, error="Vaqtida chiqarilmadi."
    )
    due = list(approved.filter(publish_at__lte=now).values_list("pk", flat=True))
    for pk in due:
        publish.delay(pk)
    return len(due)


@shared_task(acks_late=False, soft_time_limit=100, time_limit=120)
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
