import logging

from django.utils import translation
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.request import get_client_ip

from .serializers import LeadAcceptedSerializer, LeadCreateSerializer
from .services import LeadInput, submit_lead

logger = logging.getLogger(__name__)

UTM_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")


class LeadCreateView(APIView):
    """Landing'dagi ariza formasi. Autentifikatsiya shart emas (CSRF ham talab qilinmaydi)."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "leads"

    @extend_schema(
        request=LeadCreateSerializer,
        responses={201: LeadAcceptedSerializer},
        tags=["leads"],
    )
    def post(self, request: Request) -> Response:
        serializer = LeadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("website"):
            # Bot: javob odatdagidek, lekin ariza saqlanmaydi.
            logger.info("Honeypot ishladi, ariza o'tkazib yuborildi")
            return Response({"status": "ok"}, status=status.HTTP_201_CREATED)

        submit_lead(
            LeadInput(
                name=data["name"],
                phone=data["phone"],
                course=data.get("course"),
                comment=data.get("comment", ""),
                locale=translation.get_language() or "uz",
                source_page=data.get("source_page", ""),
                utm={key: data[key] for key in UTM_FIELDS if data.get(key)},
                ip=get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "")[:500],
            )
        )
        return Response({"status": "ok"}, status=status.HTTP_201_CREATED)
