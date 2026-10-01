"""Claude API bilan ishlash: bitta "qadam" (model javobi), streaming va xarajat hisobi.

Agent sikli (agent.py) modelni `ChatModel` interfeysi orqali chaqiradi: haqiqiy Claude
(`AnthropicModel`) va oflayn rejim (`rules.RuleModel`) bir xil ko'rinishda ishlaydi.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

import anthropic
from django.conf import settings

MILLION = Decimal(1_000_000)
# Prompt caching narxi kiruvchi token narxiga nisbatan (platform.claude.com/docs → Pricing).
CACHE_WRITE_RATE = Decimal("1.25")
CACHE_READ_RATE = Decimal("0.1")
REQUEST_TIMEOUT_SECONDS = 60
# Xavfsizlik klassifikatori bor modellar: rad etilgan so'rov server tomonda boshqa modelga o'tadi.
FALLBACK_MODELS = ("claude-opus-5", "claude-fable-5-1")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class Turn:
    """Modelning bitta javobi: API bloklari (tarixga aynan shunday qo'shiladi) va sarf."""

    content: list[dict[str, Any]]
    stop_reason: str
    model: str
    usage: Usage = field(default_factory=Usage)

    @property
    def text(self) -> str:
        return "".join(block["text"] for block in self.content if block["type"] == "text").strip()

    @property
    def tool_calls(self) -> list[ToolCall]:
        return [
            ToolCall(id=block["id"], name=block["name"], input=block["input"])
            for block in self.content
            if block["type"] == "tool_use"
        ]


class ChatModel(Protocol):
    name: str

    def respond(
        self,
        *,
        system: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        allow_tools: bool,
        on_text: Callable[[str], None],
    ) -> Turn: ...


def cost_usd(usage: Usage) -> Decimal:
    """Javob narxi (USD). Narxlar `.env`da: ASSISTANT_PRICE_INPUT / ASSISTANT_PRICE_OUTPUT."""
    price_in = Decimal(str(settings.ASSISTANT_PRICE_INPUT))
    price_out = Decimal(str(settings.ASSISTANT_PRICE_OUTPUT))
    total = (
        usage.input_tokens * price_in
        + usage.cache_write_tokens * price_in * CACHE_WRITE_RATE
        + usage.cache_read_tokens * price_in * CACHE_READ_RATE
        + usage.output_tokens * price_out
    )
    return (total / MILLION).quantize(Decimal("0.000001"))


def with_cache_breakpoint(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Oxirgi xabarning oxirgi blokiga kesh belgisi: keyingi so'rovda butun tarix keshdan o'qiladi.

    Belgi saqlanmaydi (nusxaga qo'yiladi) — aks holda tarixda 4 tadan ko'p belgi to'planib qoladi.
    """
    if not messages:
        return messages
    *head, last = messages
    content = [dict(block) for block in last["content"]]
    content[-1]["cache_control"] = {"type": "ephemeral"}
    return [*head, {**last, "content": content}]


def replay_blocks(blocks: list[Any]) -> list[dict[str, Any]]:
    """Javob bloklari → tarixga aynan qaytariladigan dict'lar.

    * `thinking` / `redacted_thinking` o'zgarishsiz qoladi: joriy modellar standart holatda
      fikrlaydi va vosita chaqiruvidan keyingi so'rovda bu bloklar imzosi bilan qaytishi shart.
    * Rad etilgan javob boshqa modelda davom etgan bo'lsa (`fallback` bloki), chegaradan oldingi
      fikrlash va vosita chaqiruvlari tashlanadi — matn qoladi (Claude API qoidasi).
    """
    boundary = max((i for i, block in enumerate(blocks) if block.type == "fallback"), default=-1)
    result: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif index < boundary:
            continue
        elif block.type == "tool_use":
            result.append(
                {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
            )
        elif block.type == "thinking":
            result.append(
                {"type": "thinking", "thinking": block.thinking, "signature": block.signature}
            )
        elif block.type == "redacted_thinking":
            result.append({"type": "redacted_thinking", "data": block.data})
    return result


class AnthropicModel:
    """Haqiqiy Claude. Javob streaming bilan olinadi: matn kelishi bilan `on_text`ga beriladi."""

    def __init__(self, *, api_key: str, model: str, max_tokens: int, effort: str) -> None:
        self.name = model
        self.max_tokens = max_tokens
        self.effort = effort
        self.client = anthropic.Anthropic(
            api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=2
        )

    def respond(
        self,
        *,
        system: str,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        allow_tools: bool,
        on_text: Callable[[str], None],
    ) -> Turn:
        params: dict[str, Any] = {
            "model": self.name,
            # Fikrlash tokenlari ham shu chegaraga kiradi: kichik qilinsa, javob kesilib qoladi.
            "max_tokens": self.max_tokens,
            # Tizim prompti (kurslar, FAQ) hamma suhbatlar uchun bir xil — alohida keshlanadi.
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": with_cache_breakpoint(messages),
            "tools": tools,
            # Sotuv chati: tez va qisqa javob muhim — fikrlash chuqurligi past.
            "output_config": {"effort": self.effort},
        }
        if not allow_tools:
            params["tool_choice"] = {"type": "none"}
        if self.name.startswith(FALLBACK_MODELS):
            # Xavfsizlik klassifikatori so'rovni rad etsa, API uni o'zi mos modelda qayta bajaradi.
            manager: Any = self.client.beta.messages.stream(
                **params, betas=[FALLBACK_BETA], fallbacks="default"
            )
        else:
            manager = self.client.messages.stream(**params)
        with manager as stream:
            for text in stream.text_stream:
                on_text(text)
            message = stream.get_final_message()
        usage = message.usage
        return Turn(
            content=replay_blocks(message.content),
            stop_reason=message.stop_reason or "end_turn",
            model=message.model,
            usage=Usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=usage.cache_read_input_tokens or 0,
                cache_write_tokens=usage.cache_creation_input_tokens or 0,
            ),
        )
