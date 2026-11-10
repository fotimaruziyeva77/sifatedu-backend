from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import LegalPage, SiteSettings

from .access import current_center
from .models import Center
from .sections import Feature
from .sites import center_name, is_flagship, is_platform


class CenterInfoSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["center", "platform"])
    state = serializers.ChoiceField(choices=Center.State.choices)
    features = serializers.ListField(child=serializers.ChoiceField(choices=Feature.choices))
    name = serializers.CharField()
    flagship = serializers.BooleanField()
    logo = serializers.CharField(allow_blank=True)
    logo_dark = serializers.CharField(allow_blank=True)
    color = serializers.CharField(allow_blank=True)
    trial = serializers.BooleanField()
    support_phone = serializers.CharField(allow_blank=True)
    support_telegram = serializers.CharField(allow_blank=True)
    base_domain = serializers.CharField()
    legal_pages = serializers.ListField(child=serializers.CharField())
    signup_open = serializers.BooleanField()


def _brand() -> dict[str, Any]:
    if is_platform():
        return {"logo": "", "logo_dark": "", "color": "", "legal_pages": []}
    site = SiteSettings.load()
    return {
        "logo": site.logo.url if site.logo else "",
        "logo_dark": site.logo_dark.url if site.logo_dark else "",
        "color": site.brand_color,
        "legal_pages": list(LegalPage.objects.values_list("slug", flat=True)),
    }


class CenterInfoView(APIView):
    """Sayt shu javobga qarab brend, menyu va sahifalarni ko'rsatadi."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    open_when_blocked = True

    @extend_schema(responses=CenterInfoSerializer, tags=["center"])
    def get(self, request: Request) -> Response:
        center = current_center()
        data: dict[str, Any] = {
            "kind": "platform" if is_platform() else "center",
            "state": center.state if center else Center.State.ACTIVE,
            "features": sorted(center.features if center else Feature.values),
            "name": center_name(),
            "flagship": is_flagship(),
            "trial": bool(center and center.is_trial),
            "support_phone": settings.PLATFORM_SUPPORT_PHONE,
            "support_telegram": settings.PLATFORM_SUPPORT_TELEGRAM,
            "base_domain": settings.CENTERS_BASE_DOMAIN,
            "signup_open": settings.SIGNUP_OPEN,
            **_brand(),
        }
        return Response(data)
