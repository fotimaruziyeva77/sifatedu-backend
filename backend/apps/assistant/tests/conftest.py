from collections.abc import Iterator
from typing import Any

import pytest
from django.core.cache import cache

from apps.assistant.models import Conversation
from apps.catalog.models import Course

from .helpers import make_course


@pytest.fixture(autouse=True)
def _isolated(settings: Any) -> Iterator[None]:
    # Throttle va budjet hisoblagichlari keshda; .env qiymatlari testga ta'sir qilmasin.
    cache.clear()
    settings.APP_URL = "http://localhost"
    settings.GEMINI_API_KEY = ""
    settings.ASSISTANT_DRY_RUN = False
    settings.TELEGRAM_BOT_TOKEN = ""
    settings.TELEGRAM_WEBHOOK_SECRET = ""
    settings.GEMINI_PRICE_INPUT = 2.0
    settings.GEMINI_PRICE_OUTPUT = 10.0
    yield
    cache.clear()


@pytest.fixture
def courses(db: Any) -> list[Course]:
    return [
        make_course("frontend", title_uz="Frontend dasturlash", is_featured=True),
        make_course(
            "sifat-kids",
            title_uz="SIFAT Kids",
            audience=Course.Audience.KIDS,
            age_min=7,
            age_max=11,
            study_format=Course.Format.OFFLINE,
            price_online=0,
            price_offline_monthly=450_000,
        ),
        make_course("draft-kurs", status=Course.Status.DRAFT),
    ]


@pytest.fixture
def conversation(db: Any) -> Conversation:
    return Conversation.objects.create(channel=Conversation.Channel.WEB, locale="uz")
