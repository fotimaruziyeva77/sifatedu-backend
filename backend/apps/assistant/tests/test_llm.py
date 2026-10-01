"""Claude chaqiruvi: tarixga qaytariladigan bloklar va so'rov parametrlari (SDK soxta)."""

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

from apps.assistant.llm import FALLBACK_BETA, AnthropicModel, replay_blocks


def block(kind: str, **fields: Any) -> SimpleNamespace:
    return SimpleNamespace(type=kind, **fields)


def test_thinking_blocks_are_kept_for_tool_loop() -> None:
    blocks = [
        block("thinking", thinking="", signature="sig-1"),
        block("text", text="Tekshiraman", citations=None),
        block("tool_use", id="toolu_1", name="get_course", input={"slug": "frontend"}),
        block("redacted_thinking", data="xyz"),
        block("server_something", payload=1),
    ]

    assert replay_blocks(blocks) == [
        {"type": "thinking", "thinking": "", "signature": "sig-1"},
        {"type": "text", "text": "Tekshiraman"},
        {"type": "tool_use", "id": "toolu_1", "name": "get_course", "input": {"slug": "frontend"}},
        {"type": "redacted_thinking", "data": "xyz"},
    ]


def test_blocks_before_fallback_boundary_are_dropped_except_text() -> None:
    blocks = [
        block("thinking", thinking="", signature="old"),
        block("text", text="Qisman javob "),
        block("tool_use", id="toolu_old", name="show_courses", input={}),
        block("fallback", from_=None, to=None),
        block("thinking", thinking="", signature="new"),
        block("text", text="davomi"),
    ]

    assert replay_blocks(blocks) == [
        {"type": "text", "text": "Qisman javob "},
        {"type": "thinking", "thinking": "", "signature": "new"},
        {"type": "text", "text": "davomi"},
    ]


class FakeStream:
    def __init__(self, message: SimpleNamespace) -> None:
        self.message = message
        self.text_stream = iter(["Salom", "!"])

    def get_final_message(self) -> SimpleNamespace:
        return self.message


def final_message() -> SimpleNamespace:
    return SimpleNamespace(
        content=[block("thinking", thinking="", signature="s"), block("text", text="Salom!")],
        stop_reason="end_turn",
        model="claude-sonnet-5",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=100,
            cache_creation_input_tokens=None,
        ),
    )


def capture(target: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    @contextmanager
    def stream(**params: Any) -> Any:
        calls.append(params)
        yield FakeStream(final_message())

    target.stream = stream
    return calls


@pytest.mark.parametrize("allow_tools", [True, False])
def test_request_parameters(allow_tools: bool) -> None:
    model = AnthropicModel(api_key="k", model="claude-sonnet-5", max_tokens=16000, effort="low")
    calls = capture(model.client.messages)
    history = [{"role": "user", "content": [{"type": "text", "text": "Salom"}]}]
    texts: list[str] = []

    turn = model.respond(
        system="Qoidalar", tools=[], messages=history, allow_tools=allow_tools, on_text=texts.append
    )

    [params] = calls
    assert params["output_config"] == {"effort": "low"}
    assert params["max_tokens"] == 16000
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert params["messages"][-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    assert ("tool_choice" in params) is not allow_tools
    assert "betas" not in params and "fallbacks" not in params
    assert texts == ["Salom", "!"]
    assert turn.text == "Salom!"
    assert turn.content[0] == {"type": "thinking", "thinking": "", "signature": "s"}
    assert (turn.usage.cache_read_tokens, turn.usage.cache_write_tokens) == (100, 0)


def test_opus_uses_server_side_fallbacks() -> None:
    model = AnthropicModel(api_key="k", model="claude-opus-5", max_tokens=16000, effort="low")
    calls = capture(model.client.beta.messages)
    with mock.patch.object(model.client.messages, "stream") as plain:
        model.respond(
            system="Qoidalar",
            tools=[],
            messages=[{"role": "user", "content": [{"type": "text", "text": "Salom"}]}],
            allow_tools=True,
            on_text=lambda _text: None,
        )

    plain.assert_not_called()
    [params] = calls
    assert params["betas"] == [FALLBACK_BETA]
    assert params["fallbacks"] == "default"
