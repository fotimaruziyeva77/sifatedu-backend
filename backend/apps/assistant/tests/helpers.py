"""Testlar uchun: kurs yaratish va soxta model (oldindan yozilgan javoblar)."""

import copy
from collections.abc import Callable
from typing import Any

from apps.assistant.llm import Turn, Usage
from apps.catalog.models import Category, Course


def make_course(slug: str, **extra: Any) -> Course:
    category, _ = Category.objects.get_or_create(slug="dasturlash", defaults={"name_uz": "IT"})
    defaults: dict[str, Any] = {
        "title_uz": slug.replace("-", " ").title(),
        "status": Course.Status.PUBLISHED,
        "study_format": Course.Format.BOTH,
        "price_online": 1_200_000,
        "price_offline_monthly": 600_000,
    }
    return Course.objects.create(slug=slug, category=category, **{**defaults, **extra})


def text_turn(text: str, usage: Usage | None = None) -> Turn:
    return Turn(
        content=[{"type": "text", "text": text}],
        stop_reason="end_turn",
        model="fake",
        usage=usage or Usage(),
    )


def tool_turn(name: str, data: dict[str, Any], call_id: str = "toolu_1") -> Turn:
    return Turn(
        content=[{"type": "tool_use", "id": call_id, "name": name, "input": data}],
        stop_reason="tool_use",
        model="fake",
    )


class ScriptedModel:
    """Soxta Claude: oldindan yozilgan javoblarni qaytaradi va unga nima yuborilganini eslaydi."""

    name = "fake"

    def __init__(self, turns: list[Turn]) -> None:
        self.turns = list(turns)
        self.calls: list[dict[str, Any]] = []

    def respond(
        self,
        *,
        system: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        allow_tools: bool,
        on_text: Callable[[str], None],
    ) -> Turn:
        self.calls.append(
            {"system": system, "messages": copy.deepcopy(messages), "allow_tools": allow_tools}
        )
        turn = self.turns.pop(0)
        if turn.text:
            on_text(turn.text)
        return turn
