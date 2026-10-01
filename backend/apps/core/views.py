import logging

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import defaults
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Health: DB ishlamayapti")
        return False
    return True


def _cache_ok() -> bool:
    try:
        cache.set("health:ping", "pong", timeout=10)
        return cache.get("health:ping") == "pong"
    except Exception:
        logger.exception("Health: Redis ishlamayapti")
        return False


class HealthView(APIView):
    """Docker healthcheck va monitoring uchun."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        responses=inline_serializer(
            "Health",
            fields={
                "status": serializers.ChoiceField(choices=["ok", "error"]),
                "checks": serializers.DictField(child=serializers.BooleanField()),
            },
        ),
        tags=["system"],
    )
    def get(self, request: Request) -> Response:
        checks = {"database": _database_ok(), "cache": _cache_ok()}
        healthy = all(checks.values())
        return Response(
            {"status": "ok" if healthy else "error", "checks": checks},
            status=200 if healthy else 503,
        )


def _is_api(request: HttpRequest) -> bool:
    return request.path.startswith("/api/")


def not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    if _is_api(request):
        return JsonResponse({"error": {"code": "not_found", "message": "Topilmadi."}}, status=404)
    return defaults.page_not_found(request, exception)


def server_error(request: HttpRequest) -> HttpResponse:
    if _is_api(request):
        return JsonResponse(
            {"error": {"code": "server_error", "message": "Serverda xatolik yuz berdi."}},
            status=500,
        )
    return defaults.server_error(request)
