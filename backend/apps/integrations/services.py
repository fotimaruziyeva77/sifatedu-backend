"""Markaz o'z botini, Click va Eskiz hisobini ulaydi. Maxfiy qiymatlar hech qayerga yozilmaydi."""

import logging
import secrets

from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions

from apps.bot.appearance import apply_profile
from apps.notifications import sms, telegram
from apps.tenancy.sites import center_name, site_url

from .models import Integrations

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/api/v1/bot/webhook/"
ALLOWED_UPDATES = ["message", "callback_query", "my_chat_member"]


class BadCredentials(exceptions.APIException):
    status_code = 400
    default_code = "bad_credentials"


class ServiceUnavailable(exceptions.APIException):
    status_code = 503
    default_code = "service_unavailable"
    default_detail = _("Xizmat javob bermadi. Birozdan keyin qayta urinib ko'ring.")


def webhook_url() -> str:
    return f"{site_url()}{WEBHOOK_PATH}"


def set_webhook(token: str, secret: str) -> bool:
    """Telegram faqat https manzilga yuboradi: local'da o'tkazib yuboriladi (polling)."""
    url = webhook_url()
    if not url.startswith("https://"):
        logger.info("Webhook o'rnatilmadi: manzil https emas")
        return False
    telegram.call(
        "setWebhook",
        {"url": url, "secret_token": secret, "allowed_updates": ALLOWED_UPDATES},
        token=token,
    )
    return True


def connect_telegram(token: str) -> Integrations:
    """Tokenni Telegram'da tekshiradi, keyin saqlaydi va botni shu markazga bog'laydi."""
    try:
        me = telegram.call("getMe", {}, token=token)
    except telegram.TelegramError as exc:
        raise BadCredentials(_("Token noto'g'ri. BotFather bergan tokenni kiriting.")) from exc
    except OSError as exc:
        raise ServiceUnavailable from exc
    username = str((me or {}).get("username") or "") if isinstance(me, dict) else ""
    if not username:
        raise BadCredentials(_("Token noto'g'ri. BotFather bergan tokenni kiriting."))

    row = Integrations.load()
    secret = row.telegram_webhook_secret or secrets.token_urlsafe(32)
    try:
        set_webhook(token, secret)
        apply_profile(token=token)
    except (OSError, telegram.TelegramError) as exc:
        raise ServiceUnavailable from exc
    row.telegram_token = token
    row.telegram_username = username
    row.telegram_webhook_secret = secret
    row.save(
        update_fields=[
            "telegram_token",
            "telegram_username",
            "telegram_webhook_secret",
            "updated_at",
        ]
    )
    telegram.forget_username()
    return row


def disconnect_telegram() -> Integrations:
    """Webhook o'chiriladi (bo'lmasa, Telegram yuborishda davom etadi), keyin token."""
    row = Integrations.load()
    if row.telegram_token:
        try:
            telegram.call("deleteWebhook", {}, token=row.telegram_token)
        except (OSError, telegram.TelegramError) as exc:
            logger.warning("Webhook o'chirilmadi: %s", exc)
    row.telegram_token = ""
    row.telegram_username = ""
    row.telegram_login = False
    row.save(update_fields=["telegram_token", "telegram_username", "telegram_login", "updated_at"])
    telegram.forget_username()
    return row


def connect_eskiz(email: str, password: str, sender: str) -> Integrations:
    try:
        valid = sms.can_login(email, password)
    except OSError as exc:
        raise ServiceUnavailable from exc
    if not valid:
        raise BadCredentials(_("Eskiz email yoki paroli noto'g'ri."))
    row = Integrations.load()
    row.eskiz_email = email
    row.eskiz_password = password
    row.eskiz_from = sender
    row.eskiz_brand = center_name()
    row.save(
        update_fields=["eskiz_email", "eskiz_password", "eskiz_from", "eskiz_brand", "updated_at"]
    )
    sms.forget_token()
    return row
