from collections.abc import Iterator
from typing import Any
from unittest import mock

import pytest
from django.utils import timezone

from apps.notifications import telegram
from apps.users.models import SocialAccount, User


@pytest.fixture(autouse=True)
def bot(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    settings.TELEGRAM_BOT_USERNAME = "sifat_test_bot"
    settings.SMS_DRY_RUN = True
    settings.APP_URL = "https://sifatedu.uz"


@pytest.fixture
def sent() -> Iterator[mock.MagicMock]:
    """Telegram'ga ketgan xabarlar (tarmoqqa chiqilmaydi)."""
    with mock.patch.object(telegram, "send_message") as send:
        yield send


def make_student(
    phone: str = "+998901234567",
    *,
    telegram_id: int | None = None,
    consent: bool = False,
    locale: str = "uz",
    **extra: Any,
) -> User:
    user = User.objects.create_user(
        phone=phone,
        password="x",
        first_name="Aziz",
        locale=locale,
        marketing_consent_at=timezone.now() if consent else None,
        **extra,
    )
    if telegram_id is not None:
        SocialAccount.objects.create(
            user=user, provider=SocialAccount.Provider.TELEGRAM, uid=str(telegram_id)
        )
    return user
