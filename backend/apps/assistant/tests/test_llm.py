"""Gemini chaqiruvi: tarix → `contents`, so'rov sozlamalari, stream'dan javob va imzolar
(SDK chaqirilmaydi — soxta mijoz)."""

import base64
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from google.genai import types

from apps.assistant.llm import GeminiModel, Turn, to_contents
from apps.assistant.tools import TOOLS

SIGNATURE = b"\x01signature-bytes"
ENCODED = base64.b64encode(SIGNATURE).decode()


def chunk(
    *parts: types.Part,
    finish: types.FinishReason | None = None,
    usage: types.GenerateContentResponseUsageMetadata | None = None,
    blocked: bool = False,
) -> types.GenerateContentResponse:
    candidate = types.Candidate(
        content=types.Content(role="model", parts=list(parts)), finish_reason=finish
    )
    feedback = (
        types.GenerateContentResponsePromptFeedback(block_reason=types.BlockedReason.SAFETY)
        if blocked
        else None
    )
    return types.GenerateContentResponse(
        candidates=[] if blocked else [candidate],
        usage_metadata=usage,
        prompt_feedback=feedback,
        model_version="gemini-3.8-flash-001",
    )


def model_with(
    chunks: list[types.GenerateContentResponse], *, thinking: str = "low"
) -> tuple[GeminiModel, list[dict[str, Any]]]:
    model = GeminiModel(api_key="k", model="gemini-3.8-flash", max_tokens=16000, thinking=thinking)
    calls: list[dict[str, Any]] = []

    def stream(**params: Any) -> Iterator[types.GenerateContentResponse]:
        calls.append(params)
        return iter(chunks)

    model.client = SimpleNamespace(models=SimpleNamespace(generate_content_stream=stream))  # type: ignore[assignment]
    return model, calls


def ask(model: GeminiModel, *, allow_tools: bool = True) -> tuple[Turn, list[str]]:
    texts: list[str] = []
    turn = model.respond(
        system="Qoidalar",
        tools=TOOLS,
        messages=[{"role": "user", "content": [{"type": "text", "text": "Salom"}]}],
        allow_tools=allow_tools,
        on_text=texts.append,
    )
    return turn, texts


def test_history_becomes_gemini_contents() -> None:
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "<kontekst>…</kontekst>"},
                {"type": "text", "text": "Kurslar?"},
            ],
        },
        {
            "role": "assistant",
            "content": [
                # Avvalgi model (Claude) davridan qolgan fikrlash bloki — Gemini'ga bormaydi.
                {"type": "thinking", "thinking": "", "signature": "eski"},
                {"type": "text", "text": "Tekshiraman"},
                {
                    "type": "tool_use",
                    "id": "fc-1",
                    "call_id": "fc-1",
                    "name": "get_course",
                    "input": {"slug": "python"},
                    "signature": ENCODED,
                },
                {"type": "tool_use", "id": "toolu_x", "name": "show_courses", "input": {}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "fc-1", "content": '{"slug": "python"}'},
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_x",
                    "content": "Kurs topilmadi",
                    "is_error": True,
                },
            ],
        },
        {"role": "assistant", "content": [{"type": "text", "text": "Mana", "signature": ENCODED}]},
    ]

    contents = to_contents(messages)

    assert [content.role for content in contents] == ["user", "model", "user", "model"]
    assert [part.text for part in contents[0].parts or []] == ["<kontekst>…</kontekst>", "Kurslar?"]
    text, call, legacy = contents[1].parts or []
    assert text.text == "Tekshiraman" and text.thought_signature is None
    assert call.function_call is not None and call.thought_signature == SIGNATURE
    assert (call.function_call.id, call.function_call.name) == ("fc-1", "get_course")
    assert call.function_call.args == {"slug": "python"}
    # Gemini bermagan ID (Claude yoki oddiy rejim) qaytarilmaydi.
    assert legacy.function_call is not None and legacy.function_call.id is None
    found, failed = contents[2].parts or []
    assert found.function_response is not None and failed.function_response is not None
    assert (found.function_response.id, found.function_response.name) == ("fc-1", "get_course")
    assert found.function_response.response == {"result": {"slug": "python"}}
    assert failed.function_response.name == "show_courses"
    assert failed.function_response.response == {"error": "Kurs topilmadi"}
    assert (contents[3].parts or [])[0].thought_signature == SIGNATURE


def test_stream_collects_text_signature_and_usage() -> None:
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=1000,
        cached_content_token_count=800,
        candidates_token_count=50,
        thoughts_token_count=30,
    )
    model, _calls = model_with(
        [
            chunk(types.Part(text="Assalomu ")),
            chunk(types.Part(text="alaykum!")),
            # Imzo oxirgi, matni bo'sh qismda keladi.
            chunk(
                types.Part(text="", thought_signature=SIGNATURE),
                finish=types.FinishReason.STOP,
                usage=usage,
            ),
        ]
    )

    turn, texts = ask(model)

    assert texts == ["Assalomu ", "alaykum!"]
    assert turn.content == [{"type": "text", "text": "Assalomu alaykum!", "signature": ENCODED}]
    assert (turn.stop_reason, turn.model) == ("end_turn", "gemini-3.8-flash-001")
    # Keshdagi tokenlar alohida (10 barobar arzon), fikrlash — chiqish narxida.
    assert (turn.usage.input_tokens, turn.usage.cache_read_tokens) == (200, 800)
    assert turn.usage.output_tokens == 80


def test_function_calls_keep_id_and_signature() -> None:
    call = types.FunctionCall(id="fc-7", name="show_courses", args={"slugs": ["python"]})
    model, _calls = model_with(
        [
            chunk(
                types.Part(function_call=call, thought_signature=SIGNATURE),
                types.Part(function_call=types.FunctionCall(name="get_course", args={})),
                finish=types.FinishReason.STOP,
            )
        ]
    )

    turn, texts = ask(model)

    first, second = turn.content
    assert first == {
        "type": "tool_use",
        "id": "fc-7",
        "call_id": "fc-7",
        "name": "show_courses",
        "input": {"slugs": ["python"]},
        "signature": ENCODED,
    }
    # Parallel chaqiruvda imzo faqat birinchisida; ID bo'lmasa — o'zimiz qo'yamiz.
    assert second["id"].startswith("gemini_") and "call_id" not in second
    assert "signature" not in second
    assert turn.stop_reason == "tool_use" and texts == []
    # Saqlangan blok keyingi so'rovda aynan qaytadi.
    replayed = to_contents([{"role": "assistant", "content": turn.content}])
    assert (replayed[0].parts or [])[0].thought_signature == SIGNATURE


@pytest.mark.parametrize("allow_tools", [True, False])
def test_request_config(allow_tools: bool) -> None:
    model, calls = model_with([chunk(types.Part(text="Salom"), finish=types.FinishReason.STOP)])

    ask(model, allow_tools=allow_tools)

    [params] = calls
    config: types.GenerateContentConfig = params["config"]
    assert params["model"] == "gemini-3.8-flash"
    assert config.system_instruction == "Qoidalar"
    assert config.max_output_tokens == 16000
    assert config.thinking_config is not None
    assert config.thinking_config.thinking_level == types.ThinkingLevel.LOW
    assert config.automatic_function_calling is not None
    assert config.automatic_function_calling.disable is True
    mode = config.tool_config.function_calling_config.mode  # type: ignore[union-attr]
    expected = (
        types.FunctionCallingConfigMode.AUTO
        if allow_tools
        else types.FunctionCallingConfigMode.NONE
    )
    assert mode == expected
    [tool] = config.tools or []
    declared = {item.name: item for item in tool.function_declarations or []}  # type: ignore[union-attr]
    assert set(declared) == {"get_course", "show_courses", "create_lead"}
    schema = declared["create_lead"].parameters_json_schema
    assert isinstance(schema, dict) and "additionalProperties" not in schema
    assert schema["required"] == ["phone", "topic", "summary"]


@pytest.mark.parametrize(
    ("finish", "blocked", "expected"),
    [
        (types.FinishReason.SAFETY, False, "refusal"),
        (types.FinishReason.PROHIBITED_CONTENT, False, "refusal"),
        (None, True, "refusal"),
        (types.FinishReason.MAX_TOKENS, False, "max_tokens"),
    ],
)
def test_stop_reasons(finish: types.FinishReason | None, blocked: bool, expected: str) -> None:
    model, _calls = model_with([chunk(types.Part(text="…"), finish=finish, blocked=blocked)])

    turn, _texts = ask(model)

    assert turn.stop_reason == expected


def test_unknown_thinking_level_falls_back_to_low() -> None:
    model, _calls = model_with([], thinking="extreme")

    assert model.thinking == "low"
