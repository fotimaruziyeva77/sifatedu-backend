"""Gemini'siz oddiy javob beruvchi: test rejimi va zaxira.

Qachon ishlaydi: `ASSISTANT_DRY_RUN=true` (local, E2E), kunlik yoki oylik budjet tugaganda,
suhbatdagi xabarlar limiti oshganda va Gemini API xato berganda. U AI emas — faqat kurslarni
ko'rsatadi va raqam so'raydi; raqam yozilsa ariza baribir yaratiladi, ya'ni mijoz yo'qolmaydi.
Agent bilan bir xil interfeys (`ChatModel`) va bir xil vositalardan foydalanadi.
"""

import json
import uuid
from collections.abc import Callable
from typing import Any

from .llm import Turn
from .phones import PLACEHOLDER_RE
from .prompt import published_courses

PHRASES = {
    "uz": {
        "prefix": "🧪 Test rejimi (AI ulanmagan). ",
        "courses": (
            "Mana kurslarimizdan bir nechtasi. Bepul maslahat uchun ismingiz va telefon "
            "raqamingizni yozing — menejerimiz qo'ng'iroq qiladi."
        ),
        "ask_phone": (
            "Savolingizga menejerimiz aniq javob beradi. Ismingiz va telefon raqamingizni "
            "yozib qoldiring — ish vaqtida qo'ng'iroq qilamiz."
        ),
        "thanks": "Rahmat! Arizangiz qabul qilindi. Menejerimiz ish vaqtida qo'ng'iroq qiladi.",
        "thanks_hours": (
            "Rahmat! Arizangiz qabul qilindi. Menejerimiz ish vaqtida ({hours}) qo'ng'iroq qiladi."
        ),
    },
    "ru": {
        "prefix": "🧪 Тестовый режим (ИИ не подключён). ",
        "courses": (
            "Вот несколько наших курсов. Для бесплатной консультации напишите имя и номер "
            "телефона — менеджер перезвонит."
        ),
        "ask_phone": (
            "На этот вопрос точно ответит наш менеджер. Оставьте имя и номер телефона — "
            "перезвоним в рабочее время."
        ),
        "thanks": "Спасибо! Заявка принята. Менеджер позвонит в рабочее время.",
        "thanks_hours": "Спасибо! Заявка принята. Менеджер позвонит в рабочее время ({hours}).",
    },
    "en": {
        "prefix": "🧪 Test mode (AI is not connected). ",
        "courses": (
            "Here are some of our courses. For a free consultation, leave your name and phone "
            "number — a manager will call you."
        ),
        "ask_phone": (
            "Our manager will answer this precisely. Leave your name and phone number — we will "
            "call you during working hours."
        ),
        "thanks": "Thank you! Your request is received. A manager will call during working hours.",
        "thanks_hours": (
            "Thank you! Your request is received. A manager will call during working hours "
            "({hours})."
        ),
    },
}
KIDS_WORDS = (
    "bola", "farzand", "o'g'l", "qiz", "kids", "ребен", "дет", "сын", "доч", "child", "kid",
    "son", "daughter",
)  # fmt: skip


def pick_courses(text: str) -> list[str]:
    """Matnga mos 3 ta kurs (kalit so'z bo'yicha), topilmasa — tavsiya etilganlari."""
    words = text.lower()
    courses = published_courses()
    kids = [course.slug for course in courses if course.audience == "KIDS"]
    matched = [
        course.slug
        for course in courses
        if any(part in words for part in course.slug.split("-") if len(part) > 3)
    ]
    if any(word in words for word in KIDS_WORDS):
        matched = [*kids, *matched]
    picked = list(dict.fromkeys(matched)) or [course.slug for course in courses]
    return picked[:3]


def _is_tool_result(message: dict[str, Any]) -> bool:
    return any(block.get("type") == "tool_result" for block in message["content"])


def _user_text(message: dict[str, Any]) -> str:
    texts = [block["text"] for block in message["content"] if block.get("type") == "text"]
    return texts[-1] if texts else ""


class RuleModel:
    def __init__(self, *, locale: str, dry_run: bool) -> None:
        self.name = "rules-dry-run" if dry_run else "rules"
        self.dry_run = dry_run
        self.phrases = PHRASES.get(locale, PHRASES["uz"])

    def respond(
        self,
        *,
        system: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        allow_tools: bool,
        on_text: Callable[[str], None],
    ) -> Turn:
        last = messages[-1]
        if _is_tool_result(last):
            return self._say(self._after_tools(last), on_text)

        text = _user_text(last)
        placeholder = PLACEHOLDER_RE.search(text)
        if placeholder and allow_tools:
            return self._call(
                "create_lead",
                {
                    "phone": placeholder.group(0),
                    "name": "",
                    "topic": "enrollment",
                    "course_slug": "",
                    "study_format": "UNKNOWN",
                    "summary": f"AI'siz rejimda qoldirilgan raqam. Mijoz yozgan: {text[:200]}",
                },
            )
        first = sum(1 for item in messages if item["role"] == "user" and not _is_tool_result(item))
        if allow_tools and first == 1:
            slugs = pick_courses(text)
            if slugs:
                return self._call("show_courses", {"slugs": slugs})
        return self._say(self.phrases["ask_phone"], on_text)

    def _after_tools(self, message: dict[str, Any]) -> str:
        for block in message["content"]:
            if block.get("type") != "tool_result" or block.get("is_error"):
                continue
            try:
                data = json.loads(block.get("content") or "{}")
            except ValueError:
                continue
            if data.get("saved"):
                hours = data.get("manager_working_hours")
                return (
                    self.phrases["thanks_hours"].format(hours=hours)
                    if hours
                    else self.phrases["thanks"]
                )
            if data.get("shown"):
                return self.phrases["courses"]
        return self.phrases["ask_phone"]

    def _say(self, text: str, on_text: Callable[[str], None]) -> Turn:
        text = f"{self.phrases['prefix']}{text}" if self.dry_run else text
        on_text(text)
        return Turn(
            content=[{"type": "text", "text": text}], stop_reason="end_turn", model=self.name
        )

    def _call(self, name: str, data: dict[str, Any]) -> Turn:
        block = {
            "type": "tool_use",
            "id": f"rule_{uuid.uuid4().hex[:12]}",
            "name": name,
            "input": data,
        }
        return Turn(content=[block], stop_reason="tool_use", model=self.name)
