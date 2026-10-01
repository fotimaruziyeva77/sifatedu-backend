"""AI maslahatchi API: saytdagi chat (Telegram bot webhook'i — apps/bot).

Saytda suhbat HttpOnly cookie orqali topiladi (kalitning o'zi bazada saqlanmaydi, faqat xeshi).
Javob Celery'da tayyorlanadi; sayt `GET /assistant/chat/` bilan yangi xabarlar va yozilayotgan
matnni so'rab turadi.
"""

import hashlib
import secrets
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone, translation
from django.utils.crypto import salted_hmac
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.request import get_client_ip

from .agent import ai_configured, partial_key
from .models import AssistantSettings, Conversation, Message
from .phones import unmask
from .serializers import ChatRateSerializer, ChatSendSerializer, ChatStateSerializer
from .service import add_user_message, attach_user_phone, claim, is_pending, release
from .tasks import answer

COOKIE_NAME = "sifat_chat"
COOKIE_PATH = "/api/v1/assistant/"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def chat_enabled() -> bool:
    return AssistantSettings.load().enabled and ai_configured()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_conversation(request: Request) -> Conversation | None:
    token = request.COOKIES.get(COOKIE_NAME)
    if not token:
        return None
    return Conversation.objects.filter(
        token_hash=token_hash(token),
        channel=Conversation.Channel.WEB,
        anonymized_at__isnull=True,
    ).first()


def chat_state(conversation: Conversation | None, after: int = 0) -> dict[str, Any]:
    if conversation is None:
        return {"conversation": None, "messages": [], "draft": ""}
    visible = conversation.messages.filter(
        pk__gt=after, role__in=[Message.Role.USER, Message.Role.ASSISTANT]
    ).order_by("id")
    messages = [
        {
            "id": message.pk,
            "role": "user" if message.role == Message.Role.USER else "assistant",
            "text": message.text,
            "attachments": message.attachments,
            "rating": message.rating,
            "created_at": message.created_at,
        }
        for message in visible
        if message.text or message.attachments
    ]
    pending = is_pending(conversation)
    draft = cache.get(partial_key(conversation.pk), "") if pending else ""
    return {
        "conversation": {
            "id": conversation.pk,
            "status": conversation.status,
            "pending": pending,
            "has_lead": conversation.lead_id is not None,
        },
        "messages": messages,
        "draft": unmask(draft, conversation.phones),
    }


class CsrfForAllMixin:
    """Mehmon uchun ham CSRF tekshiriladi (DRF faqat kirgan foydalanuvchida tekshiradi)."""

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # type: ignore[misc]
        if request.method not in SAFE_METHODS:
            SessionAuthentication().enforce_csrf(request)


class ChatView(CsrfForAllMixin, APIView):
    permission_classes = [AllowAny]
    throttle_scope = "assistant"

    def get_throttles(self) -> list[BaseThrottle]:
        # Holatni so'rash (javob kutilayotganda har ~0,7 soniyada) umumiy limit bilan cheklanadi,
        # yozish esa qo'shimcha `assistant` limiti bilan.
        throttles = super().get_throttles()
        if self.request.method == "POST":
            throttles.append(ScopedRateThrottle())
        return throttles

    @extend_schema(
        parameters=[OpenApiParameter("after", int, description="Shu ID'dan keyingi xabarlar")],
        responses=ChatStateSerializer,
        tags=["assistant"],
    )
    def get(self, request: Request) -> Response:
        try:
            after = max(int(request.query_params.get("after", 0)), 0)
        except ValueError:
            after = 0
        return Response(chat_state(current_conversation(request), after))

    @extend_schema(
        request=ChatSendSerializer,
        responses={
            202: ChatStateSerializer,
            409: OpenApiResponse(description="Oldingi javob hali tayyorlanyapti"),
            503: OpenApiResponse(description="AI maslahatchi o'chirilgan"),
        },
        tags=["assistant"],
    )
    def post(self, request: Request) -> Response:
        if not chat_enabled():
            return Response(
                {"detail": _("AI maslahatchi hozir o'chirilgan.")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = ChatSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        conversation = current_conversation(request)
        token = None
        if conversation is None or conversation.status == Conversation.Status.CLOSED:
            token = secrets.token_urlsafe(32)
            ip = get_client_ip(request) or ""
            conversation = Conversation.objects.create(
                channel=Conversation.Channel.WEB,
                token_hash=token_hash(token),
                locale=translation.get_language() or "uz",
                source_page=data.get("page", "")[:500],
                ip_hash=salted_hmac("assistant-ip", ip).hexdigest() if ip else "",
                last_message_at=timezone.now(),
            )

        announce = False
        user = request.user
        if user.is_authenticated and conversation.user_id != user.pk:
            conversation.user = user
            conversation.name = conversation.name or user.first_name
            attach_user_phone(conversation, user.phone)
            conversation.save(update_fields=["user", "name", "phones", "updated_at"])
            announce = True

        if not claim(conversation):
            return Response(
                {"detail": _("Oldingi savolingizga javob yozilyapti."), "code": "busy"},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            add_user_message(
                conversation,
                data["text"],
                page=data.get("page", ""),
                quiz=data.get("quiz"),
                announce_user=announce,
            )
        except Exception:
            release(conversation)
            raise
        conversation_id = conversation.pk
        transaction.on_commit(lambda: answer.delay(conversation_id))

        response = Response(chat_state(conversation), status=status.HTTP_202_ACCEPTED)
        if token is not None:
            response.set_cookie(
                COOKIE_NAME,
                token,
                max_age=COOKIE_MAX_AGE,
                path=COOKIE_PATH,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=True,
                samesite="Lax",
            )
        return response

    @extend_schema(responses={204: None}, tags=["assistant"])
    def delete(self, request: Request) -> Response:
        """Yangi suhbat: cookie o'chiriladi, eski suhbat admin uchun saqlanib qoladi."""
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH, samesite="Lax")
        return response


class ChatRateView(CsrfForAllMixin, APIView):
    """AI javobiga 👍/👎 — yomon baholanganlarni admin ko'rib chiqadi."""

    permission_classes = [AllowAny]

    @extend_schema(request=ChatRateSerializer, responses={204: None}, tags=["assistant"])
    def post(self, request: Request) -> Response:
        serializer = ChatRateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        conversation = current_conversation(request)
        updated = (
            Message.objects.filter(
                pk=data["message"], conversation=conversation, role=Message.Role.ASSISTANT
            ).update(rating=data["rating"] or None)
            if conversation is not None
            else 0
        )
        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
