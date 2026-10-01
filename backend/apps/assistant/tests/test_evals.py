"""Eval tekshiruvlari: til, bazada yo'q narx, vositalar va ariza."""

import pytest

from apps.assistant.evals import Scenario, check, language_of
from apps.assistant.models import Conversation, Message
from apps.catalog.models import Course

pytestmark = pytest.mark.django_db


def reply(conversation: Conversation, text: str, tools: tuple[str, ...] = ()) -> None:
    content = [{"type": "tool_use", "id": name, "name": name, "input": {}} for name in tools]
    Message.objects.create(
        conversation=conversation, role=Message.Role.ASSISTANT, text=text, content=content
    )


def test_language_detection() -> None:
    assert language_of("Salom! Sizga qaysi kurs kerak?") == "uz"
    assert language_of("Здравствуйте, чем помочь?") == "ru"
    assert language_of("Hello, which course do you like?") == "en"


def test_good_answer_passes(conversation: Conversation, courses: list[Course]) -> None:
    reply(conversation, "Frontend kursi onlayn 1 200 000 so'm, bir marta to'lanadi.")

    assert check(Scenario("uz", "uz", ["?"], forbid_tools={"create_lead"}), conversation) == []


def test_problems_are_reported(conversation: Conversation, courses: list[Course]) -> None:
    reply(conversation, "Kurs 990 000 so'm turadi, 50% chegirma beramiz!", tools=("create_lead",))
    scenario = Scenario(
        "uz",
        "uz",
        ["?"],
        tools={"show_courses"},
        forbid_tools={"create_lead"},
        lead=True,
        must_not_contain=["chegirma beramiz"],
    )

    problems = check(scenario, conversation)

    assert "bazada yo'q narx: 990 000" in problems
    assert "chaqirilmagan vosita: show_courses" in problems
    assert "keraksiz vosita: create_lead" in problems
    assert "ariza yaratilmadi" in problems
    assert "bo'lmasligi kerak: 'chegirma beramiz'" in problems
