"""Agent sikli: vositalar, tarix, xarajat, budjet va zaxira rejim."""

from decimal import Decimal
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from google.genai import errors as gemini_errors

from apps.assistant import agent
from apps.assistant.agent import api_history, choose_model, partial_key, respond
from apps.assistant.llm import GeminiModel, Turn, Usage, cost_usd
from apps.assistant.models import AssistantSettings, Conversation, Message
from apps.assistant.rules import RuleModel
from apps.assistant.service import add_user_message
from apps.catalog.models import Course
from apps.leads.models import Lead

from .helpers import ScriptedModel, text_turn, tool_turn

pytestmark = pytest.mark.django_db


def run_with(model: ScriptedModel, conversation: Conversation) -> list[Message]:
    with mock.patch.object(agent, "choose_model", return_value=model):
        return respond(conversation)


def test_plain_answer_is_saved_with_cost(conversation: Conversation) -> None:
    add_user_message(conversation, "Salom")
    usage = Usage(input_tokens=100, output_tokens=50, cache_read_tokens=1000, cache_write_tokens=0)
    model = ScriptedModel([text_turn("Assalomu alaykum! Qanday yordam beray?", usage)])

    [message] = run_with(model, conversation)

    assert message.role == Message.Role.ASSISTANT
    assert message.text == "Assalomu alaykum! Qanday yordam beray?"
    # 100×2 + 1000×2×0.1 + 50×10 = 900 → $0.0009
    assert message.cost_usd == Decimal("0.000900")
    conversation.refresh_from_db()
    assert conversation.cost_usd == Decimal("0.000900")
    assert conversation.last_message_at is not None


def test_tool_loop_shows_cards_on_final_answer(
    conversation: Conversation, courses: list[Course]
) -> None:
    add_user_message(conversation, "Qaysi kurs bor?")
    model = ScriptedModel(
        [
            tool_turn("show_courses", {"slugs": ["frontend", "yoq-kurs"]}),
            text_turn("Sizga Frontend kursi mos."),
        ]
    )

    created = run_with(model, conversation)

    assert [message.text for message in created] == ["", "Sizga Frontend kursi mos."]
    assert [card["slug"] for card in created[-1].attachments] == ["frontend"]
    # Vosita natijasi modelga qaytgan: topilmagan kurs ham aytilgan.
    tool_result = model.calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_1"
    assert tool_result["name"] == "show_courses"  # Gemini natijani vosita nomi bilan kutadi
    assert "yoq-kurs" in tool_result["content"]
    assert Message.objects.filter(conversation=conversation, role=Message.Role.TOOL).count() == 1


def test_model_never_sees_real_phone(conversation: Conversation, courses: list[Course]) -> None:
    add_user_message(conversation, "Aziz, raqamim 90 123 45 67")
    model = ScriptedModel(
        [
            tool_turn(
                "create_lead",
                {
                    "phone": "‹telefon-1›",
                    "name": "Aziz",
                    "topic": "enrollment",
                    "summary": "Frontend",
                },
            ),
            text_turn("Rahmat, ‹telefon-1› raqamiga qo'ng'iroq qilamiz."),
        ]
    )

    with mock.patch("apps.leads.services.notify_new_lead.delay"):
        created = run_with(model, conversation)

    sent = str(model.calls)
    assert "901234567" not in sent and "‹telefon-1›" in sent
    lead = Lead.objects.get()
    assert lead.phone == "+998901234567"
    assert lead.source == Lead.Source.AI_WEB
    # Mijozga ko'rsatiladigan matnda raqam ochiladi.
    assert created[-1].text == "Rahmat, +998901234567 raqamiga qo'ng'iroq qilamiz."


def test_history_replays_exact_blocks_for_cache(conversation: Conversation) -> None:
    add_user_message(conversation, "Birinchi savol")
    run_with(ScriptedModel([text_turn("Birinchi javob")]), conversation)
    add_user_message(conversation, "Ikkinchi savol")
    model = ScriptedModel([text_turn("Ikkinchi javob")])

    run_with(model, conversation)

    sent = model.calls[0]["messages"]
    assert [item["role"] for item in sent] == ["user", "assistant", "user"]
    first_user = Message.objects.filter(role=Message.Role.USER).first()
    assert first_user is not None
    assert sent[0]["content"] == first_user.content


def test_unanswered_tool_call_is_dropped_from_history(conversation: Conversation) -> None:
    add_user_message(conversation, "Savol")
    # Jarayon uzilgan: vosita chaqirilgan, lekin natija saqlanmagan.
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=[
            {"type": "text", "text": "Tekshiraman"},
            {"type": "tool_use", "id": "toolu_x", "name": "get_course", "input": {}},
        ],
    )
    add_user_message(conversation, "Javob bormi?")

    history = api_history(conversation)

    assert [item["role"] for item in history] == ["user", "assistant", "user"]
    assert history[1]["content"] == [{"type": "text", "text": "Tekshiraman"}]


def test_last_step_forbids_tools(conversation: Conversation, courses: list[Course]) -> None:
    add_user_message(conversation, "Kurslar")
    turns = [tool_turn("show_courses", {"slugs": ["frontend"]}, f"t{n}") for n in range(3)]
    model = ScriptedModel([*turns, text_turn("Yakuniy javob")])

    created = run_with(model, conversation)

    assert [call["allow_tools"] for call in model.calls] == [True, True, True, False]
    assert created[-1].text == "Yakuniy javob"


def test_api_error_falls_back_to_rules(conversation: Conversation) -> None:
    add_user_message(conversation, "Salom")
    failing = mock.Mock(name="gemini")
    failing.respond.side_effect = gemini_errors.ServerError(
        503, {"error": {"code": 503, "message": "overloaded", "status": "UNAVAILABLE"}}
    )

    with (
        mock.patch.object(agent, "choose_model", return_value=failing),
        mock.patch.object(agent, "alert") as alert,
    ):
        created = respond(conversation)

    alert.assert_called_once()
    assert created[-1].model == "rules"
    assert "telefon" in created[-1].text


def test_unexpected_error_still_answers(conversation: Conversation) -> None:
    add_user_message(conversation, "Salom")
    broken = mock.Mock(name="gemini")
    broken.respond.side_effect = RuntimeError("boom")

    with (
        mock.patch.object(agent, "choose_model", return_value=broken),
        mock.patch.object(agent, "alert"),
    ):
        created = respond(conversation)

    assert created[-1].model == "fallback"
    assert cache.get(partial_key(conversation.pk)) is None


def test_choose_model(settings: Any, conversation: Conversation) -> None:
    config = AssistantSettings.load()
    assert isinstance(choose_model(conversation, config), RuleModel)

    # Test rejimi kalit bo'lsa ham ustun.
    settings.GEMINI_API_KEY = "test-key"
    settings.ASSISTANT_DRY_RUN = True
    dry = choose_model(conversation, config)
    assert isinstance(dry, RuleModel) and dry.dry_run
    settings.ASSISTANT_DRY_RUN = False

    settings.GEMINI_MODEL = "gemini-3.8-flash"
    settings.GEMINI_THINKING_LEVEL = "medium"
    gemini = choose_model(conversation, config)
    assert isinstance(gemini, GeminiModel)
    assert (gemini.name, gemini.thinking) == ("gemini-3.8-flash", "medium")

    config.daily_budget_usd = Decimal("0.01")
    Message.objects.create(conversation=conversation, role="ASSISTANT", cost_usd=Decimal("0.02"))
    with mock.patch("apps.assistant.budget.alert") as alert:
        fallback = choose_model(conversation, config)
    assert isinstance(fallback, RuleModel) and not fallback.dry_run
    alert.assert_called_once()

    config.daily_budget_usd = Decimal("5")
    conversation.user_messages = config.max_user_messages + 1
    assert isinstance(choose_model(conversation, config), RuleModel)


def test_cost() -> None:
    usage = Usage(input_tokens=1000, output_tokens=200, cache_read_tokens=0, cache_write_tokens=0)
    assert cost_usd(usage) == Decimal("0.004000")
    # Keshdan o'qilgan tokenlar — kiruvchi narxning 10 foizi: 1000×2×0.1 / 1M.
    assert cost_usd(Usage(cache_read_tokens=1000)) == Decimal("0.000200")


def test_refusal_without_text_still_answers(conversation: Conversation) -> None:
    add_user_message(conversation, "Salom")
    refused = Turn(content=[], stop_reason="refusal", model="fake")

    created = run_with(ScriptedModel([refused]), conversation)

    assert created[-1].model == "fallback"
    assert "telefon" in created[-1].text


def test_unreadable_answer_falls_back_to_rules(conversation: Conversation) -> None:
    add_user_message(conversation, "Salom")
    broken = mock.Mock(name="gemini")
    broken.respond.side_effect = ValueError("response is not valid")

    with (
        mock.patch.object(agent, "choose_model", return_value=broken),
        mock.patch.object(agent, "alert"),
    ):
        created = respond(conversation)

    assert created[-1].model == "rules"


def test_thinking_only_answer_is_not_replayed(conversation: Conversation) -> None:
    # Claude davridan qolgan, faqat fikrlashdan iborat javob tarixga qo'shilmaydi.
    add_user_message(conversation, "Savol")
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=[{"type": "thinking", "thinking": "", "signature": "s"}],
    )
    add_user_message(conversation, "Yana savol")

    assert [item["role"] for item in api_history(conversation)] == ["user"]


def test_signature_travels_with_tool_call(
    conversation: Conversation, courses: list[Course]
) -> None:
    add_user_message(conversation, "Kurslar")
    first = tool_turn("show_courses", {"slugs": ["frontend"]}, "fc-1")
    first.content[0].update(call_id="fc-1", signature="c2ln")
    model = ScriptedModel([first, text_turn("Mana")])

    run_with(model, conversation)

    replayed = model.calls[1]["messages"][-2]
    assert replayed["role"] == "assistant"
    assert replayed["content"][0]["signature"] == "c2ln"
    assert replayed["content"][0]["call_id"] == "fc-1"
