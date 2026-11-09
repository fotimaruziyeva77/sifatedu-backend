from celery import shared_task
from django.conf import settings

from apps.videos import s3

from .access import current_center
from .limits import _staff_count, _student_count
from .models import Center
from .storage import center_prefix

CENTERS_FOLDER = "centers/"


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
