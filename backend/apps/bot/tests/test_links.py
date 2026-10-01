"""Sayt ↔ bot: "Telegram'da ishlash" havolasi, botdan saytga parolsiz kirish, webhook."""

from typing import Any
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from rest_framework.test import APIClient

from apps.bot import links
from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.notifications import telegram
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.users.models import SocialAccount
from apps.users.roles import Role

from .conftest import (
    APP,
    SENDER,
    TG_ID,
    FakeTelegram,
    World,
    connect,
    contact,
    make_user,
    message,
)

pytestmark = pytest.mark.django_db


def api(user: Any = None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def quiz_link(world: World, quiz: Quiz | None = None) -> Any:
    return api(world.student).post(f"/api/v1/bot/quizzes/{(quiz or world.quiz).pk}/link/")


def payload_of(url: str) -> str:
    return parse_qs(urlparse(url).query)["start"][0]


def test_site_link_starts_quiz_in_bot_and_connects_telegram(tg: FakeTelegram, world: World) -> None:
    response = quiz_link(world)
    assert response.status_code == 200
    url = response.json()["url"]
    assert url.startswith("https://t.me/sifat_test_bot?start=q_")

    handle_update(message(f"/start {payload_of(url)}"))

    account = SocialAccount.objects.get(uid=str(TG_ID))
    assert account.user == world.student
    # Saytdan kelgan odamga til so'ralmaydi — sayt tili olinadi.
    assert BotChat.objects.get(chat_id=TG_ID).language == "uz"
    assert any("Telegram ulandi" in text for text in tg.texts)
    assert "1/5." in tg.last["text"]

    # Havola bir martalik.
    tg.clear()
    handle_update(message(f"/start {payload_of(url)}"))
    assert "eskirgan" in tg.texts[0]


def test_site_link_opened_from_someone_elses_telegram(tg: FakeTelegram, world: World) -> None:
    connect(make_user("+998907770000", Role.STUDENT, name="Boshqa"))
    url = quiz_link(world).json()["url"]

    handle_update(message(f"/start {payload_of(url)}"))

    assert "boshqa" in tg.texts[0]
    assert not SocialAccount.objects.filter(user=world.student).exists()
    assert not world.student.quiz_attempts.exists()


def test_quiz_link_respects_locks_and_bot_setup(
    tg: FakeTelegram, world: World, settings: Any
) -> None:
    second = Quiz.objects.create(lesson=world.lessons[1], title="CSS")
    import_questions(second, parse("? CSS nima?\n+ Uslublar\n- Dastur\n"))

    assert quiz_link(world, second).status_code == 403
    assert api().post(f"/api/v1/bot/quizzes/{world.quiz.pk}/link/").status_code == 403

    # Bot sozlanmagan: Telegram'dan bot nomini ham olib bo'lmaydi.
    settings.TELEGRAM_BOT_TOKEN = ""
    settings.TELEGRAM_BOT_USERNAME = ""
    tg.errors["getMe"] = telegram.TelegramNotConfiguredError()
    assert quiz_link(world).status_code == 404


def test_login_link_signs_in_once(tg: FakeTelegram, world: World) -> None:
    path = f"/dashboard/courses/frontend/lessons/{world.lessons[0].pk}"
    url = links.login_url(world.student, path, connect(world.student))
    client = APIClient()

    first = client.get(url.removeprefix(APP))
    assert first.status_code == 302
    assert first["Location"] == f"{APP}/uz{path}"
    assert first["Referrer-Policy"] == "no-referrer"
    assert client.session["_auth_user_id"] == str(world.student.pk)

    # Ishlatilgan havola: kirish sahifasi, keyin o'sha sahifaga qaytadi.
    again = APIClient().get(url.removeprefix(APP))
    assert again["Location"] == f"{APP}/uz/auth/login?{urlencode({'next': path})}"


def test_login_link_is_never_issued_for_staff(tg: FakeTelegram, world: World) -> None:
    url = links.login_url(world.teacher, "/dashboard", connect(world.teacher))

    assert url == f"{APP}/uz/dashboard"


def test_login_link_needs_phone_confirmed_in_telegram(tg: FakeTelegram, world: World) -> None:
    """Saytdagi havola bilan ulangan Telegram (masalan, umumiy kompyuterdagi birovniki) — saytga
    parolsiz kira olmaydi, toki raqamini kontakt bilan tasdiqlamaguncha."""
    url = quiz_link(world).json()["url"]
    handle_update(message(f"/start {payload_of(url)}"))
    chat = BotChat.objects.get(chat_id=TG_ID)
    assert links.login_url(world.student, "/dashboard", chat) == f"{APP}/uz/dashboard"

    # Boshqa raqam — tasdiq emas.
    handle_update(contact("+998907770000"))
    chat.refresh_from_db()
    assert chat.verified_phone == ""
    handle_update(contact(world.student.phone))
    chat.refresh_from_db()
    assert chat.verified_phone == world.student.phone
    assert "/api/v1/bot/login/" in links.login_url(world.student, "/dashboard", chat)


def test_login_link_rejects_foreign_redirects(tg: FakeTelegram) -> None:
    response = APIClient().get("/api/v1/bot/login/nope/?next=//evil.example/x")

    assert response["Location"] == f"{APP}/uz/auth/login?next=%2Fdashboard"


def test_webhook_accepts_private_updates_only(settings: Any) -> None:
    client = APIClient()
    press = {
        "update_id": 5,
        "callback_query": {
            "id": "1",
            "from": SENDER,
            "data": "news",
            "message": {"message_id": 3, "chat": {"id": TG_ID, "type": "private"}},
        },
    }
    group = {"update_id": 6, "message": {"chat": {"id": -100, "type": "supergroup"}}}
    # Bot kanalga administrator qilindi — kanal ID si admin uchun eslab qolinadi.
    channel = {
        "update_id": 7,
        "my_chat_member": {
            "chat": {"id": -100123, "type": "channel", "title": "Sifat Edu"},
            "new_chat_member": {"status": "administrator"},
        },
    }
    with mock.patch("apps.bot.views.handle_update.delay") as queued:
        assert client.post("/api/v1/bot/webhook/", press, format="json").status_code == 403

        settings.TELEGRAM_WEBHOOK_SECRET = "s3cret"
        wrong = client.post(
            "/api/v1/bot/webhook/", press, format="json", HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="x"
        )
        right = client.post(
            "/api/v1/bot/webhook/",
            press,
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="s3cret",
        )
        ignored = client.post(
            "/api/v1/bot/webhook/",
            group,
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="s3cret",
        )

        admin_event = client.post(
            "/api/v1/bot/webhook/",
            channel,
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="s3cret",
        )

    assert wrong.status_code == 403
    assert right.status_code == 200 and ignored.status_code == 200
    assert admin_event.status_code == 200
    assert [call.args[0] for call in queued.call_args_list] == [press, channel]


def test_bot_name_lookup_failure_is_not_retried_at_once(tg: FakeTelegram, settings: Any) -> None:
    settings.TELEGRAM_BOT_USERNAME = ""
    tg.errors["getMe"] = OSError("Telegram javob bermadi")

    assert telegram.bot_username() == telegram.bot_username() == ""
    # Dars sahifalari har safar Telegram'ni kutib qolmaydi.
    assert len(tg.of("getMe")) == 1
