from celery import shared_task

from apps.learning.models import Enrollment

from . import services
from .models import Certificate


@shared_task
def check_certificate(user_id: int, course_id: int) -> str:
    certificate = services.check(user_id, course_id)
    return certificate.number if certificate else ""


@shared_task
def sweep_certificates() -> str:
    """Har kecha: hodisa o'tkazib yuborilgan bo'lsa ham (masalan, o'qituvchi eski vazifani
    qabul qilgan) shartlari bajarilganlarga sertifikat."""
    have = set(Certificate.objects.values_list("user_id", "course_id"))
    rows = Enrollment.objects.filter(
        status=Enrollment.Status.ACTIVE,
        course__certificate=True,
        user__is_active=True,
        user__is_staff=False,
    ).values_list("user_id", "course_id")
    issued = sum(1 for row in rows if row not in have and services.check(*row) is not None)
    return f"{issued}"
