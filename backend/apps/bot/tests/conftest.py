"""Bot testlari: Telegram Bot API o'rniga soxta server (tarmoqqa chiqilmaydi)."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache

from apps.bot.models import BotChat
from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning.models import Enrollment, StudyGroup
from apps.notifications import telegram
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.users.models import SocialAccount, User
from apps.users.roles import Role, set_roles

TG_ID = 5001
SENDER = {
    "id": TG_ID,
    "is_bot": False,
    "first_name": "Aziz",
    "username": "aziz",
    "language_code": "uz",
}
APP = "https://sifatedu.uz"


@dataclass
class FakeTelegram:
    """Chaqiruvlarni yozib boradi va Telegram kabi javob qaytaradi."""

    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    uploads: list[dict[str, Any]] = field(default_factory=list)
    members: dict[int, str] = field(default_factory=dict)
    errors: dict[str, Exception] = field(default_factory=dict)
    next_id: int = 100

    def __call__(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        timeout: float = 10,
        files: dict[str, Any] | None = None,
    ) -> Any:
        self.calls.append((method, payload))
        if files:
            self.uploads.append({"method": method, "files": files, **payload})
        if method in self.errors:
            raise self.errors[method]
        if method in ("sendMessage", "sendPhoto"):
            self.next_id += 1
            result: dict[str, Any] = {
                "message_id": self.next_id,
                "chat": {"id": payload["chat_id"]},
            }
            if method == "sendPhoto":
                result["photo"] = [{"file_id": "small"}, {"file_id": "photo-file-id"}]
            return result
        if method == "getChatMember":
            return {"status": self.members.get(payload["user_id"], "left")}
        if method == "getMe":
            return {"username": "sifat_test_bot"}
        return True

    def of(self, method: str) -> list[dict[str, Any]]:
        return [payload for name, payload in self.calls if name == method]

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self.of("sendMessage")

    @property
    def texts(self) -> list[str]:
        return [str(payload["text"]) for payload in self.messages]

    @property
    def last(self) -> dict[str, Any]:
        return self.messages[-1]

    @property
    def edits(self) -> list[dict[str, Any]]:
        return self.of("editMessageText")

    @property
    def notices(self) -> list[str]:
        return [str(item.get("text", "")) for item in self.of("answerCallbackQuery")]

    def clear(self) -> None:
        self.calls.clear()


def buttons(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Xabar ostidagi tugmalar (bitta ro'yxatda)."""
    markup = payload.get("reply_markup") or {}
    return [item for row in markup.get("inline_keyboard", []) for item in row]


def keyboard(payload: dict[str, Any]) -> list[str]:
    """Pastki menyu tugmalari matni."""
    markup = payload.get("reply_markup") or {}
    return [item["text"] for row in markup.get("keyboard", []) for item in row]


def message(text: str = "", sender: dict[str, Any] = SENDER, **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "message_id": 1,
        "chat": {"id": sender["id"], "type": "private"},
        "from": sender,
        **extra,
    }
    if text:
        body["text"] = text
    return {"update_id": 1, "message": body}


def press(data: str, message_id: int = 77, sender: dict[str, Any] = SENDER) -> dict[str, Any]:
    return {
        "update_id": 2,
        "callback_query": {
            "id": "cb-1",
            "from": sender,
            "data": data,
            "message": {"message_id": message_id, "chat": {"id": sender["id"], "type": "private"}},
        },
    }


def contact(phone: str, user_id: int = TG_ID, sender: dict[str, Any] = SENDER) -> dict[str, Any]:
    return message(
        sender=sender, contact={"phone_number": phone, "user_id": user_id, "first_name": "Aziz"}
    )


@pytest.fixture(autouse=True)
def bot_settings(settings: Any) -> Iterator[None]:
    cache.clear()
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    settings.TELEGRAM_BOT_USERNAME = "sifat_test_bot"
    settings.APP_URL = APP
    settings.SMS_DRY_RUN = True
    yield
    cache.clear()


@pytest.fixture
def tg() -> Iterator[FakeTelegram]:
    fake = FakeTelegram()
    with mock.patch.object(telegram, "call", fake):
        yield fake


def make_user(phone: str, *roles: str, name: str = "Aziz", locale: str = "uz") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name, locale=locale)
    if roles:
        set_roles(user, roles)
    return user


def connect(
    user: User, chat_id: int = TG_ID, *, language: str = "uz", verified: bool = True
) -> BotChat:
    """Telegram'i ulangan va botda til tanlagan o'quvchi (standart — raqami kontakt bilan
    tasdiqlangan)."""
    SocialAccount.objects.create(
        user=user, provider=SocialAccount.Provider.TELEGRAM, uid=str(chat_id)
    )
    return BotChat.objects.create(
        chat_id=chat_id,
        first_name=user.first_name,
        language=language,
        verified_phone=user.phone if verified else "",
    )


# Besh turdagi savol (apps/quizzes/tests dagi kabi), to'g'ri javoblar matn bo'yicha.
SOURCE = """
? HTML nimaning qisqartmasi?
+ HyperText Markup Language
- High Tech Modern Language
> Izoh: HTML — sahifa tuzilmasi uchun belgilash tili.

? Qaysilari HTML teglari?
+ <div>
+ <p>
- <color>

? Eng katta sarlavha tegi qaysi?
= h1

? Brauzer sahifani qanday tayyorlaydi?
1. HTML o'qiladi
2. CSS qo'llanadi
3. JavaScript ishga tushadi

? Moslang:
HTML :: tuzilma
CSS :: ko'rinish
JavaScript :: harakat
"""


@dataclass
class World:
    course: Course
    lessons: list[Lesson]
    quiz: Quiz
    student: User
    teacher: User
    group: StudyGroup


@pytest.fixture
def world(db: Any) -> World:
    """Onlayn guruh: 3 dars, birinchisida 5 savolli test; o'quvchining Telegram'i ulangan."""
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="frontend", title_uz="Frontend", category=category)
    module = Module.objects.create(course=course, title_uz="HTML")
    lessons = [
        Lesson.objects.create(module=module, title_uz=f"Dars {index}", order=index)
        for index in range(1, 4)
    ]
    quiz = Quiz.objects.create(lesson=lessons[0], title="HTML asoslari", shuffle_questions=False)
    import_questions(quiz, parse(SOURCE))
    student = make_user("+998901000001", Role.STUDENT)
    teacher = make_user("+998901000002", Role.TEACHER, name="Ustoz")
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="FE-1", study_format="ONLINE"
    )
    Enrollment.objects.create(user=student, course=course, group=group)
    return World(course, lessons, quiz, student, teacher, group)
