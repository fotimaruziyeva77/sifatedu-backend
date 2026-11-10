"""Hozirgi markazning kalitlari. Platforma (`public`) o'zinikini `.env`dan oladi: server
ogohlantirishlari va markaz ochishdagi SMS."""

from dataclasses import dataclass

from django.conf import settings
from django_tenants.utils import get_public_schema_name

from apps.tenancy.db import connection

from .models import Integrations


@dataclass(frozen=True)
class Telegram:
    token: str = ""
    username: str = ""
    webhook_secret: str = ""
    leads_chat: str = ""
    reports_chat: str = ""
    login: bool = False


@dataclass(frozen=True)
class Click:
    service_id: str = ""
    merchant_id: str = ""
    merchant_user_id: str = ""
    secret_key: str = ""
    tin: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.service_id and self.secret_key)


@dataclass(frozen=True)
class Eskiz:
    email: str = ""
    password: str = ""
    sender: str = ""
    brand: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.email and self.password)


def _row() -> Integrations | None:
    if connection.schema_name == get_public_schema_name():
        return None
    return Integrations.load()


def telegram() -> Telegram:
    row = _row()
    if row is None:
        return Telegram(token=settings.TELEGRAM_BOT_TOKEN)
    return Telegram(
        token=row.telegram_token,
        username=row.telegram_username,
        webhook_secret=row.telegram_webhook_secret,
        leads_chat=row.telegram_leads_chat_id,
        reports_chat=row.telegram_reports_chat_id,
        login=row.telegram_login,
    )


def click() -> Click:
    row = _row()
    if row is None:
        return Click()
    return Click(
        service_id=row.click_service_id,
        merchant_id=row.click_merchant_id,
        merchant_user_id=row.click_merchant_user_id,
        secret_key=row.click_secret_key,
        tin=row.click_tin,
    )


def eskiz() -> Eskiz:
    row = _row()
    if row is None:
        return Eskiz(settings.ESKIZ_EMAIL, settings.ESKIZ_PASSWORD, settings.ESKIZ_FROM)
    return Eskiz(
        row.eskiz_email,
        row.eskiz_password,
        row.eskiz_from or settings.ESKIZ_FROM,
        row.eskiz_brand,
    )
