"""Bot: /start → til → majburiy obuna → telefon orqali ro'yxatdan o'tish yoki ulanish."""

from typing import Any

import pytest

from apps.bot import subscription
from apps.bot.models import BotChat, RequiredChannel
from apps.bot.router import handle_update
from apps.notifications.telegram import TelegramError
from apps.users.models import SocialAccount, User
from apps.users.roles import Role
from apps.users.services import referral_code

from .conftest import (
    APP,
    SENDER,
    TG_ID,
    FakeTelegram,
    buttons,
    connect,
    contact,
    keyboard,
    make_user,
    message,
    press,
)

pytestmark = pytest.mark.django_db


def begin(tg: FakeTelegram, payload: str = "") -> None:
    """/start va o'zbek tilini tanlash."""
    handle_update(message(f"/start {payload}".strip()))
    handle_update(press("lang:uz"))


def test_start_asks_language_once_then_offers_signup(tg: FakeTelegram) -> None:
    handle_update(message("/start"))

    [question] = tg.messages
    assert "Tilni tanlang" in question["text"]
    assert [item["callback_data"] for item in buttons(question)] == [
        "lang:uz",
        "lang:ru",
        "lang:en",
    ]

    handle_update(press("lang:uz"))

    assert tg.edits[-1]["text"] == "✅ 🇺🇿 O'zbekcha"
    welcome = tg.last
    assert "Assalomu alaykum, Aziz!" in welcome["text"]
    assert f'<a href="{APP}/uz/offer">' in welcome["text"]
    assert welcome["reply_markup"]["keyboard"][0][0] == {
        "text": "📱 Telefonni yuborish",
        "request_contact": True,
    }
    assert BotChat.objects.get(chat_id=TG_ID).language == "uz"

    tg.clear()
    handle_update(message("/start"))
    assert len(tg.messages) == 1 and "Assalomu alaykum" in tg.last["text"]


def test_russian_speaker_gets_russian_texts(tg: FakeTelegram) -> None:
    handle_update(message("/start"))
    handle_update(press("lang:ru"))

    assert "Здравствуйте, Aziz!" in tg.last["text"]
    assert "📱 Отправить телефон" in keyboard(tg.last)


def test_required_channel_is_asked_until_joined(tg: FakeTelegram) -> None:
    RequiredChannel.objects.create(title="Sifat Edu", chat="@sifatedu", url="https://t.me/sifatedu")

    begin(tg)

    ask = tg.last
    assert "obuna bo'ling" in ask["text"]
    assert [item.get("url") or item.get("callback_data") for item in buttons(ask)] == [
        "https://t.me/sifatedu",
        "sub",
    ]
    # Obunasiz menyu ham ishlamaydi.
    handle_update(contact("+998901234567"))
    assert not User.objects.exists()

    handle_update(press("sub"))
    assert "Hali obuna bo'lmadingiz" in tg.notices[-1]

    tg.members[TG_ID] = "member"
    handle_update(press("sub"))
    assert "Assalomu alaykum" in tg.last["text"]
    # O'tgani eslab qolinadi: keyingi xabarda qayta so'ralmaydi.
    calls = len(tg.of("getChatMember"))
    handle_update(message("/help"))
    assert len(tg.of("getChatMember")) == calls


def test_channel_check_fails_open_and_is_reported(tg: FakeTelegram) -> None:
    channel = RequiredChannel.objects.create(
        title="Sifat Edu", chat="@sifatedu", url="https://t.me/sifatedu"
    )
    tg.errors["getChatMember"] = TelegramError(400, "Bad Request: member list is inaccessible")

    begin(tg)

    assert "Assalomu alaykum" in tg.last["text"]
    assert subscription.problems() == [(channel, "Bad Request: member list is inaccessible")]


def test_contact_creates_account_with_referral(tg: FakeTelegram) -> None:
    friend = make_user("+998907770000", Role.STUDENT, name="Do'st")
    code = referral_code(friend)
    handle_update(message(f"/start r_{code}"))
    handle_update(press("lang:uz"))

    handle_update(contact("998901234567"))

    user = User.objects.get(phone="+998901234567")
    assert user.referred_by == friend
    assert user.first_name == "Aziz" and user.terms_accepted_at is not None
    assert user.has_usable_password() is False
    assert SocialAccount.objects.get(user=user).uid == str(TG_ID)
    registered, site = tg.messages[-2:]
    assert "Akkaunt ochildi" in registered["text"]
    assert "📚 Kurslarim" in keyboard(registered)
    [login] = buttons(site)
    assert login["url"].startswith(f"{APP}/api/v1/bot/login/")
    chat = BotChat.objects.get(chat_id=TG_ID)
    assert (chat.referral_code, chat.verified_phone) == ("", "+998901234567")


def test_contact_links_existing_student_and_replaces_old_telegram(tg: FakeTelegram) -> None:
    student = make_user("+998901234567", Role.STUDENT)
    SocialAccount.objects.create(user=student, provider=SocialAccount.Provider.TELEGRAM, uid="1")
    begin(tg)

    handle_update(contact("+998 90 123 45 67"))

    assert User.objects.count() == 1
    assert SocialAccount.objects.get(user=student).uid == str(TG_ID)
    assert "Telegram akkauntingizga ulandi, Aziz" in tg.messages[-2]["text"]


def test_staff_phone_is_never_linked_by_contact(tg: FakeTelegram) -> None:
    make_user("+998901234567", Role.TEACHER, name="Ustoz")
    begin(tg)

    handle_update(contact("+998901234567"))

    assert not SocialAccount.objects.exists()
    assert "xodim akkauntiga tegishli" in tg.last["text"]


@pytest.mark.parametrize(
    ("phone", "user_id", "reply"),
    [
        ("+998901234567", 999, "o'zingizning raqamingizni"),
        ("+79991234567", TG_ID, "faqat O'zbekiston raqamlari"),
    ],
)
def test_foreign_or_non_uz_contact_is_refused(
    tg: FakeTelegram, phone: str, user_id: int, reply: str
) -> None:
    begin(tg)

    handle_update(contact(phone, user_id=user_id))

    assert not User.objects.exists()
    assert reply in tg.last["text"]


def test_linked_student_sees_menu(tg: FakeTelegram) -> None:
    connect(make_user("+998901234567", Role.STUDENT))

    handle_update(message("/start"))

    assert "Xush kelibsiz, Aziz" in tg.last["text"]
    assert keyboard(tg.last) == [
        "✅ Bugungi topshiriqlar",
        "📚 Kurslarim",
        "📝 Testlar",
        "📅 Jadval",
        "🎁 Do'stni taklif qilish",
        "💬 Savol berish",
        "⚙️ Sozlamalar",
    ]


def test_menu_needs_account(tg: FakeTelegram) -> None:
    begin(tg)

    handle_update(message("📚 Kurslarim"))

    assert "avval ro'yxatdan o'ting" in tg.last["text"]


def test_group_chats_are_ignored(tg: FakeTelegram) -> None:
    update: dict[str, Any] = message("/start")
    update["message"]["chat"]["type"] = "group"

    handle_update(update)

    assert not tg.calls and not BotChat.objects.exists()


def test_block_and_return(tg: FakeTelegram) -> None:
    user = make_user("+998901234567", Role.STUDENT)
    connect(user)

    def membership(status: str) -> dict[str, Any]:
        return {
            "update_id": 3,
            "my_chat_member": {
                "chat": {"id": TG_ID, "type": "private"},
                "from": SENDER,
                "new_chat_member": {"status": status, "user": {"id": 1, "is_bot": True}},
            },
        }

    handle_update(membership("kicked"))
    blocked = (
        BotChat.objects.get(chat_id=TG_ID).blocked_at,
        SocialAccount.objects.get(user=user).blocked_at,
    )
    handle_update(membership("member"))

    assert None not in blocked
    assert BotChat.objects.get(chat_id=TG_ID).blocked_at is None
    assert SocialAccount.objects.get(user=user).blocked_at is None


def test_channel_admin_status_is_remembered_for_admin_form(
    tg: FakeTelegram, admin_client: Any
) -> None:
    def status(value: str) -> dict[str, Any]:
        return {
            "update_id": 4,
            "my_chat_member": {
                "chat": {"id": -1001234567890, "type": "channel", "title": "Sifat Edu"},
                "from": SENDER,
                "new_chat_member": {"status": value, "user": {"id": 1, "is_bot": True}},
            },
        }

    handle_update(status("administrator"))

    # Yopiq kanalning ID si admin formasida ko'rinadi: taklif havolasidan uni bilib bo'lmaydi.
    assert subscription.admin_channels() == [(-1001234567890, "Sifat Edu")]
    page = admin_client.get("/admin/bot/requiredchannel/add/")
    assert "«Sifat Edu» — -1001234567890" in page.content.decode()
    assert not BotChat.objects.exists() and not tg.calls

    handle_update(status("left"))
    assert subscription.admin_channels() == []
