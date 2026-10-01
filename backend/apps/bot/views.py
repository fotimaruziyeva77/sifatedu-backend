"""Bot API: Telegram webhook, saytdan botga (test) va botdan saytga (parolsiz kirish) havolalar."""

from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils import translation
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.learning import access
from apps.live.gates import tasks_open
from apps.quizzes.models import Quiz
from apps.users.models import User

from . import links
from .accounts import is_staff_account
from .tasks import handle_update

FALLBACK_PAGE = "/dashboard"


def accepted(update: dict[str, Any]) -> bool:
    """Shaxsiy chatlar va botning o'z holati (kanalga administrator qilindi va h.k.). Bot a'zo
    bo'lgan guruhlardagi xabarlar (masalan, arizalar guruhi) e'tiborsiz."""
    if isinstance(update.get("my_chat_member"), dict):
        return True
    message = update.get("message")
    if isinstance(message, dict):
        return (message.get("chat") or {}).get("type") == "private"
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        return ((callback.get("message") or {}).get("chat") or {}).get("type") == "private"
    return False


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(APIView):
    """Telegram serveridan: himoya — `setWebhook`da berilgan maxfiy kalit (header)."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(exclude=True)
    def post(self, request: Request) -> Response:
        secret = settings.TELEGRAM_WEBHOOK_SECRET
        given = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secret or not constant_time_compare(given, secret):
            return Response(status=403)
        update = request.data if isinstance(request.data, dict) else {}
        if accepted(update):
            handle_update.delay(update)
        # Telegram 200 olmasa, xabarni qayta-qayta yuboraveradi.
        return Response({"ok": True})


class BotLinkSerializer(serializers.Serializer[dict[str, Any]]):
    url = serializers.CharField(help_text="https://t.me/<bot>?start=q_… — 10 daqiqa, bir marta.")


class QuizLinkView(APIView):
    """Test kartasidagi "Telegram'da ishlash": botda shu testni ochadigan bir martalik havola."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_link"

    @extend_schema(request=None, responses={200: BotLinkSerializer}, tags=["bot"])
    def post(self, request: Request, pk: int) -> Response:
        quiz = get_object_or_404(Quiz.objects.select_related("lesson__module__course"), pk=pk)
        if not access.can_open_lesson(request.user, quiz.lesson) or not tasks_open(
            request.user, quiz.lesson
        ):
            raise PermissionDenied("Bu test sizga hozircha ochiq emas.")
        user: User = request.user  # type: ignore[assignment]
        url = links.quiz_url(user, quiz.pk)
        if url is None:
            raise NotFound("Telegram bot hali sozlanmagan.")
        return Response({"url": url})


def private_redirect(url: str) -> HttpResponseRedirect:
    """Kirish havolasi boshqa saytga "Referer" bo'lib ketmasin va keshlanmasin."""
    response = HttpResponseRedirect(url)
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


class LoginLinkView(View):
    """Botdagi tugma: bir martalik token bilan saytga kiritadi va kerakli sahifani ochadi.

    Havola eskirgan yoki ishlatilgan bo'lsa — kirish sahifasi (kirgach shu sahifaga qaytadi).
    Xodim akkauntiga token bilan kirilmaydi (bot unga token bermaydi ham).
    """

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        data = links.take_login(token)
        user = User.objects.filter(pk=data["user"], is_active=True).first() if data else None
        if data is not None and user is not None and not is_staff_account(user):
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            path = links.safe_path(str(data.get("next") or "")) or FALLBACK_PAGE
            return private_redirect(links.site_url(path, user.locale or "uz"))

        wanted = links.safe_path(request.GET.get("next", "")) or FALLBACK_PAGE
        locale = (translation.get_language_from_request(request) or "uz")[:2]
        if locale not in dict(settings.LANGUAGES):
            locale = "uz"
        if request.user.is_authenticated:
            return private_redirect(links.site_url(wanted, locale))
        # Kirish sahifasi `next` ni sayt yo'li sifatida ochadi — API yo'li bo'lsa, kabinetga.
        page = FALLBACK_PAGE if wanted.startswith("/api/") else wanted
        return private_redirect(
            f"{links.base_url()}/{locale}/auth/login?{urlencode({'next': page})}"
        )
