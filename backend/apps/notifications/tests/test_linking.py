"""Telegram'ni kabinetdan ulash (bir martalik havola) va botni bloklash holati."""

from typing import Any
from unittest import mock

import pytest

from apps.assistant.models import Conversation
from apps.bot import router as bot
from apps.bot.models import BotChat
from apps.notifications import linking, telegram
from apps.users.models import SocialAccount

from .conftest import make_student

pytestmark = pytest.mark.django_db

TG_USER = {"id": 4242, "is_bot": False, "first_name": "Aziz", "language_code": "uz"}


def start(payload: str, sender: dict[str, Any] = TG_USER) -> dict[str, Any]:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "chat": {"id": sender["id"], "type": "private"},
            "from": sender,
            "text": f"/start {payload}".strip(),
        },
    }


@pytest.fixture
def replies() -> Any:
    with (
        mock.patch.object(telegram, "send_message", return_value={}) as send,
        mock.patch.object(telegram, "call"),
    ):
        yield send


def texts(replies: mock.MagicMock) -> list[str]:
    return [str(call.args[1]) for call in replies.call_args_list]


def token_from(url: str) -> str:
    assert url.startswith("https://t.me/sifat_test_bot?start=c_")
    return url.split("start=", 1)[1]


def test_link_connects_telegram_once(replies: mock.MagicMock) -> None:
    user = make_student()
    payload = token_from(linking.connect_url(user.pk) or "")

    bot.handle_update(start(payload))
    bot.handle_update(start(payload))  # havola bir martalik

    account = SocialAccount.objects.get(user=user)
    assert account.provider == SocialAccount.Provider.TELEGRAM and account.uid == "4242"
    sent = texts(replies)
    assert "Telegram ulandi" in sent[0]
    assert any("eskirgan" in text for text in sent[1:])
    # Saytdan kelgan odamga til so'ralmaydi, ulash AI suhbatini boshlamaydi.
    assert BotChat.objects.get(chat_id=4242).language == "uz"
    assert not Conversation.objects.exists()


def test_telegram_of_another_account_is_refused(replies: mock.MagicMock) -> None:
    owner = make_student("+998901000001", telegram_id=4242)
    other = make_student("+998901000002")
    payload = token_from(linking.connect_url(other.pk) or "")

    bot.handle_update(start(payload))

    assert not SocialAccount.objects.filter(user=other).exists()
    assert SocialAccount.objects.get(uid="4242").user == owner
    assert "boshqa" in texts(replies)[0]


def test_relinking_replaces_old_telegram(replies: mock.MagicMock) -> None:
    user = make_student(telegram_id=1111)
    SocialAccount.objects.filter(user=user).update(notify=False)
    payload = token_from(linking.connect_url(user.pk) or "")

    bot.handle_update(start(payload))

    account = SocialAccount.objects.get(user=user)
    assert account.uid == "4242" and account.notify


def test_plain_start_asks_language(replies: mock.MagicMock) -> None:
    bot.handle_update(start(""))

    assert not Conversation.objects.exists()
    assert "Tilni tanlang" in replies.call_args.args[1]


def test_block_and_return(replies: mock.MagicMock) -> None:
    user = make_student(telegram_id=4242)

    def membership(status: str) -> dict[str, Any]:
        return {
            "update_id": 2,
            "my_chat_member": {
                "chat": {"id": 4242, "type": "private"},
                "from": TG_USER,
                "new_chat_member": {"status": status, "user": {"id": 1, "is_bot": True}},
            },
        }

    bot.handle_update(membership("kicked"))
    blocked = SocialAccount.objects.get(user=user).blocked_at
    bot.handle_update(membership("member"))
    returned = SocialAccount.objects.get(user=user).blocked_at

    assert blocked is not None and returned is None


def test_any_message_unblocks(replies: mock.MagicMock, settings: Any) -> None:
    settings.ASSISTANT_DRY_RUN = True
    user = make_student(telegram_id=4242)
    SocialAccount.objects.filter(user=user).update(blocked_at="2026-09-01T10:00:00+05:00")

    bot.handle_update(start(""))

    assert SocialAccount.objects.get(user=user).blocked_at is None


def test_connect_url_needs_bot(settings: Any) -> None:
    settings.TELEGRAM_BOT_USERNAME = ""
    with mock.patch.object(linking.telegram, "call", side_effect=OSError("offline")):
        assert linking.connect_url(1) is None
