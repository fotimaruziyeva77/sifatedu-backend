import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.notifications.alerts import alert
from apps.videos import s3

from . import signup as flow
from .access import current_center
from .limits import PENDING_DISK_KEY, _staff_count, _student_count
from .models import Center, Signup
from .storage import center_prefix

logger = logging.getLogger(__name__)

CENTERS_FOLDER = "centers/"
SIGNUP_RETENTION_DAYS = 7
STUCK_MINUTES = 15


def disk_usage() -> int:
    """Markaz fayllari hajmi (bayt). Birinchi markaz fayllari ildizda: boshqalarnikini sanamaydi."""
    prefix = center_prefix()
    client = s3.internal()
    total = 0
    for bucket in (settings.S3_BUCKET_PRIVATE, settings.S3_BUCKET_PUBLIC):
        pages = client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
        for page in pages:
            total += sum(
                item["Size"]
                for item in page.get("Contents", [])
                if prefix or not item["Key"].startswith(CENTERS_FOLDER)
            )
    return total


@shared_task
def refresh_usage() -> None:
    """Har kecha: platforma paneli uchun sonlar va disk cheklovi uchun hajm."""
    center = current_center()
    if center is None:
        return
    Center.objects.filter(pk=center.pk).update(
        students_count=_student_count(),
        staff_count=_staff_count(),
        disk_bytes=disk_usage(),
    )
    cache.delete(PENDING_DISK_KEY)


@shared_task
def provision_center(signup_id: int) -> None:
    """Markaz ochiladi (~20 soniya). Xato bo'lsa, manzil bo'shaydi va ega qayta urinadi."""
    signup = (
        Signup.objects.select_related("plan")
        .filter(pk=signup_id, status=Signup.Status.PREPARING)
        .first()
    )
    if signup is None:
        return
    try:
        flow.provision(signup)
    except Exception:
        logger.exception("Markaz ochilmadi: ariza #%s", signup_id)
        _fail(signup)


def _fail(signup: Signup) -> None:
    try:
        flow.discard(signup)
    except Exception:
        logger.exception("Yarim ochilgan markaz o'chirilmadi: %s", signup.slug)
    Signup.objects.filter(pk=signup.pk).update(
        status=Signup.Status.FAILED, password_hash="", updated_at=timezone.now()
    )
    alert("signup:failed", f"Markaz ochilmadi: {signup.slug} (ariza #{signup.pk})")


@shared_task
def fail_stuck_signups() -> None:
    """Vazifa uzilib qolgan (deploy, xotira) arizalar «tayyorlanmoqda»da qotmasin."""
    cutoff = timezone.now() - timedelta(minutes=STUCK_MINUTES)
    stuck = Signup.objects.filter(status=Signup.Status.PREPARING, updated_at__lt=cutoff)
    for signup in stuck.select_related("plan"):
        _fail(signup)


@shared_task
def purge_signups() -> None:
    """Tugallanmagan arizalar: telefon va parol xeshi kerakligidan ortiq saqlanmaydi."""
    cutoff = timezone.now() - timedelta(days=SIGNUP_RETENTION_DAYS)
    Signup.objects.filter(
        status__in=(Signup.Status.PENDING, Signup.Status.FAILED), created_at__lt=cutoff
    ).delete()
