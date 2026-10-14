"""Bot: guruh o'quvchisining profili — to'liq ism, tasdiq, tug'ilgan sana, selfi (22d)."""

import io
from datetime import date
from typing import Any

import pytest
from PIL import Image

from apps.bot import profile, router
from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.notifications import telegram
from apps.notifications.telegram import TelegramError
from apps.users.models import User

from .conftest import TG_ID, FakeTelegram, World, buttons, connect, contact, message, press

pytestmark = pytest.mark.django_db


def selfie() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (900, 1200), "#c87a5a").save(buffer, format="JPEG")
    return buffer.getvalue()


def state(chat_id: int = TG_ID) -> dict[str, Any]:
    return BotChat.objects.get(chat_id=chat_id).state


def test_group_student_completes_the_profile_after_signup(
    tg: FakeTelegram,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: Any,
) -> None:
    # O'qituvchi o'quvchini kabinetda qo'shgan: u botga shu raqam bilan kiradi.
    handle_update(message("/start"))
    handle_update(press("lang:uz"))
    handle_update(contact(world.student.phone))

    assert "Profilingizni to'ldiring" in tg.texts[-2] and "pasportdagidek" in tg.texts[-1]

    handle_update(message("❤️ALHAMDULILLAH❤️👍"))
    assert "Tushunmadim" in tg.texts[-1]

    handle_update(message("VALIYEV AZIZ AKMAL O‘G‘LI"))
    check = tg.last
    assert "Familiya: <b>Valiyev</b>" in check["text"]
    assert "Otasining ismi: <b>Akmal o'g'li</b>" in check["text"]
    assert [item["callback_data"] for item in buttons(check)] == ["pf:ok", "pf:re"]

    handle_update(press("pf:ok"))
    student = User.objects.get(pk=world.student.pk)
    assert (student.last_name, student.first_name, student.middle_name) == (
        "Valiyev",
        "Aziz",
        "Akmal o'g'li",
    )
    assert student.profile_confirmed_at is not None and "Tug'ilgan" in tg.texts[-1]

    handle_update(message("31.02.2008"))
    assert "kun.oy.yil" in tg.texts[-1]
    handle_update(message("14.03.2008"))
    assert User.objects.get(pk=student.pk).birth_date == date(2008, 3, 14)
    ask = tg.last
    assert "selfi" in ask["text"] and buttons(ask)[0]["callback_data"] == "pf:skip"

    fetched: list[str] = []

    def download(file_id: str, *, limit: int) -> bytes:
        fetched.append(file_id)
        return selfie()

    monkeypatch.setattr(telegram, "download", download)
    sizes = [
        {"file_id": "small", "width": 90, "height": 120},
        {"file_id": "big", "width": 900, "height": 1200},
    ]
    with django_capture_on_commit_callbacks(execute=True):
        handle_update(message(photo=sizes))

    student.refresh_from_db()
    assert fetched == ["big"]
    with student.avatar.open("rb") as handle, Image.open(handle) as saved:
        assert (saved.size, saved.format) == ((512, 512), "JPEG")
    assert tg.texts[-2:] == ["⏳ Rasm saqlanmoqda…", "✅ Rahmat! Profilingiz to'ldirildi."]
    assert "profile" not in state()


def test_newcomer_without_a_group_is_not_asked(tg: FakeTelegram, world: World) -> None:
    handle_update(message("/start"))
    handle_update(press("lang:uz"))
    handle_update(contact("+998909998877"))

    assert User.objects.filter(phone="+998909998877").exists()
    assert not any("pasportdagidek" in text for text in tg.texts)
    assert "profile" not in state()


def test_profile_from_settings_photo_later_and_stale_state(
    tg: FakeTelegram, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    connect(world.student)
    handle_update(message("/profile"))
    view = tg.last
    assert "Profilim" in view["text"] and "Rasm: yo'q" in view["text"]
    assert [item["callback_data"] for item in buttons(view)] == ["pf:edit", "pf:photo"]

    handle_update(press("pf:edit"))
    assert "pasportdagidek" in tg.texts[-1]
    # 31 daqiqadan keyin yozilgan savol — ism emas, AI maslahatchiga.
    chat = BotChat.objects.get(chat_id=TG_ID)
    chat.state["profile"]["at"] -= 31 * 60
    chat.save(update_fields=["state"])
    asked: list[str] = []
    monkeypatch.setattr(router, "ask_ai", lambda chat, sender, text: asked.append(text))
    handle_update(message("Python kursi qancha turadi"))
    assert asked == ["Python kursi qancha turadi"]

    handle_update(press("pf:photo"))
    assert "selfi" in tg.texts[-1]
    handle_update(message("rasm o'rniga matn"))
    assert "Rasm yuboring" in tg.texts[-1]
    handle_update(message(document={"file_id": "doc", "mime_type": "application/pdf"}))
    assert "Bu rasm emas" in tg.texts[-1]
    handle_update(press("pf:skip"))
    assert "keyinroq" in tg.texts[-1] and "profile" not in state()


def test_photo_that_cannot_be_downloaded_can_be_sent_again(
    tg: FakeTelegram,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: Any,
) -> None:
    connect(world.student)
    handle_update(press("pf:photo"))

    def broken(file_id: str, *, limit: int) -> bytes:
        raise TelegramError(400, "Bad Request: file is too big")

    monkeypatch.setattr(telegram, "download", broken)
    with django_capture_on_commit_callbacks(execute=True):
        handle_update(message(document={"file_id": "doc", "mime_type": "image/heic"}))

    assert "Rasm saqlanmadi" in tg.texts[-1]
    assert state()["profile"]["step"] == "photo"
    assert not User.objects.get(pk=world.student.pk).avatar


def test_invitation_is_sent_once_and_starts_the_flow(tg: FakeTelegram, world: World) -> None:
    connect(world.student)

    assert profile.push(world.student) is True
    assert profile.push(world.student) is False
    invite = tg.last
    assert "Profilni to'ldirish" in buttons(invite)[0]["text"]

    handle_update(press("pf:start"))
    assert "pasportdagidek" in tg.texts[-1] and "Profilingizni" not in tg.texts[-1]
