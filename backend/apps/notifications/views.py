"""Kabinet: xabarlar ro'yxati, o'qilgan belgisi va xabarnoma sozlamalari."""

from typing import Any

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.users.models import SocialAccount, User

from . import linking
from .models import Notification
from .serializers import (
    NotificationReadSerializer,
    NotificationSerializer,
    NotificationSettingsSerializer,
    NotificationSettingsUpdateSerializer,
    TelegramConnectSerializer,
    UnreadSerializer,
)


class TelegramUnavailable(exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("Telegram bot hozircha sozlanmagan.")
    default_code = "telegram_unavailable"


def unread_count(user: User) -> int:
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


class NotificationListView(generics.ListAPIView[Notification]):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    # OpenAPI sxemasi uchun (drf-spectacular foydalanuvchisiz chaqiradi).
    queryset = Notification.objects.none()

    def get_queryset(self) -> QuerySet[Notification]:
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)  # type: ignore[misc]

    @extend_schema(tags=["notifications"])
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=NotificationReadSerializer,
        responses={200: UnreadSerializer},
        tags=["notifications"],
    )
    def post(self, request: Request) -> Response:
        serializer = NotificationReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user: User = request.user  # type: ignore[assignment]
        unread = Notification.objects.filter(user=user, read_at__isnull=True)
        ids = serializer.validated_data.get("ids")
        if ids:
            unread = unread.filter(pk__in=ids)
        unread.update(read_at=timezone.now())
        return Response({"unread": unread_count(user)})


def settings_data(user: User) -> dict[str, Any]:
    account = SocialAccount.objects.filter(
        user=user, provider=SocialAccount.Provider.TELEGRAM
    ).first()
    return {
        "telegram": {
            "available": bool(settings.TELEGRAM_BOT_TOKEN),
            "connected": account is not None,
            "notify": bool(account and account.notify),
            "blocked": bool(account and account.blocked_at),
        },
        "marketing_consent": user.marketing_consent_at is not None,
    }


class NotificationSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: NotificationSettingsSerializer}, tags=["notifications"])
    def get(self, request: Request) -> Response:
        return Response(settings_data(request.user))  # type: ignore[arg-type]

    @extend_schema(
        request=NotificationSettingsUpdateSerializer,
        responses={200: NotificationSettingsSerializer},
        tags=["notifications"],
    )
    def patch(self, request: Request) -> Response:
        serializer = NotificationSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user: User = request.user  # type: ignore[assignment]
        if "telegram_notify" in data:
            SocialAccount.objects.filter(
                user=user, provider=SocialAccount.Provider.TELEGRAM
            ).update(notify=data["telegram_notify"])
        if "marketing_consent" in data and data["marketing_consent"] != (
            user.marketing_consent_at is not None
        ):
            user.marketing_consent_at = timezone.now() if data["marketing_consent"] else None
            user.save(update_fields=["marketing_consent_at"])
        return Response(settings_data(user))


class TelegramConnectView(APIView):
    """Botga bir martalik havola: foydalanuvchi "Start" bossa, Telegram akkauntga ulanadi."""

    permission_classes = [IsAuthenticated]
    # Har bir havola yangi token: soatiga 10 ta (settings: `telegram_link`).
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_link"

    @extend_schema(request=None, responses={200: TelegramConnectSerializer}, tags=["notifications"])
    def post(self, request: Request) -> Response:
        if not settings.TELEGRAM_BOT_TOKEN:
            raise TelegramUnavailable
        user: User = request.user  # type: ignore[assignment]
        url = linking.connect_url(user.pk)
        if url is None:
            raise TelegramUnavailable
        return Response({"url": url, "expires_in": linking.TOKEN_TTL_SECONDS})
