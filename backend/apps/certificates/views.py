"""Sertifikatlar API: kabinetdagi ro'yxat va ommaviy tekshirish (raqam bo'yicha)."""

from django.utils import translation
from drf_spectacular.utils import extend_schema
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.learning import access
from apps.users.models import User

from . import services
from .models import Certificate
from .serializers import CertificateSerializer, MyCertificatesSerializer


def language(request: Request) -> str:
    return (translation.get_language() or "uz")[:2]


class MyCertificatesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="certificates_mine",
        responses={200: MyCertificatesSerializer},
        tags=["certificates"],
    )
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        locale = language(request)
        owned = list(Certificate.objects.filter(user=user).select_related("course"))
        have = {certificate.course_id for certificate in owned}
        progress = []
        for course in access.enrolled_courses(user).filter(certificate=True).order_by("order"):
            if course.pk in have:
                continue
            with translation.override(locale):
                title = str(course.title)
            progress.append(
                {
                    "course_title": title,
                    "course_slug": course.slug,
                    "requirements": [
                        {"code": item.code, "done": item.done, "total": item.total, "ok": item.ok}
                        for item in services.requirements(user, course)
                    ],
                }
            )
        return Response(
            {
                "certificates": [services.payload(item, locale) for item in owned],
                "progress": progress,
            }
        )


class VerifyView(APIView):
    """Ommaviy: sertifikat haqiqiymi, kimga va qachon berilgan (QR shu sahifaga olib keladi)."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        operation_id="certificates_verify",
        responses={200: CertificateSerializer},
        tags=["certificates"],
    )
    def get(self, request: Request, number: str) -> Response:
        certificate = get_object_or_404(
            Certificate.objects.select_related("course"), number=number.upper()
        )
        return Response(services.payload(certificate, language(request)))
