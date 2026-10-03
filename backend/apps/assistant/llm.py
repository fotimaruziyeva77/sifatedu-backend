"""Gemini API bilan ishlash: bitta "qadam" (model javobi), streaming va xarajat hisobi.

Agent sikli (agent.py) modelni `ChatModel` interfeysi orqali chaqiradi: haqiqiy Gemini
(`GeminiModel`) va oflayn rejim (`rules.RuleModel`) bir xil ko'rinishda ishlaydi.

Tarix bazada modelga bog'liq bo'lmagan bloklar bilan saqlanadi: `text`, `tool_use` (vosita
chaqiruvi) va `tool_result` (natija). Gemini qaytargan fikrlash imzosi (thought signature) blokda
`signature` (base64) bo'lib turadi va keyingi so'rovda aynan qaytariladi: Gemini 3 imzosiz vosita
chaqiruvini rad etadi (400). Gemini bergan chaqiruv ID si — `call_id`.
"""

import base64
import binascii
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MILLION = Decimal(1_000_000)
# Keshdan o'qilgan kiruvchi token oddiy narxning 10 foizi (ai.google.dev/gemini-api/docs/pricing).
CACHE_READ_RATE = Decimal("0.1")
REQUEST_TIMEOUT_MS = 60_000
RETRY_ATTEMPTS = 3
THINKING_LEVELS = ("minimal", "low", "medium", "high")
FinishReason = types.FinishReason
# Javob xavfsizlik sababli to'xtatilgan: agent oddiy "raqam qoldiring" javobiga o'tadi.
REFUSALS = {
    FinishReason.SAFETY,
    FinishReason.PROHIBITED_CONTENT,
    FinishReason.BLOCKLIST,
    FinishReason.SPII,
    FinishReason.RECITATION,
}


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
    """Modelning bitta javobi: bloklar (tarixga aynan shunday qo'shiladi) va sarf."""

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
    """Javob narxi (USD). Narxlar `.env`da: GEMINI_PRICE_INPUT / GEMINI_PRICE_OUTPUT."""
    price_in = Decimal(str(settings.GEMINI_PRICE_INPUT))
    price_out = Decimal(str(settings.GEMINI_PRICE_OUTPUT))
    total = (
        (usage.input_tokens + usage.cache_write_tokens) * price_in
        + usage.cache_read_tokens * price_in * CACHE_READ_RATE
        + usage.output_tokens * price_out
    )
    return (total / MILLION).quantize(Decimal("0.000001"))


# --- Tarix → Gemini ---


def encode(signature: bytes | None) -> str:
    return base64.b64encode(signature).decode("ascii") if signature else ""


def decode(block: dict[str, Any]) -> bytes | None:
    raw = block.get("signature")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        return None


def clean_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Vosita kiritmasi sxemasi: Gemini'ga keragi yo'q `additionalProperties` olib tashlanadi
    (vositalar kiritmani o'zi tekshiradi)."""
    cleaned = {key: value for key, value in schema.items() if key != "additionalProperties"}
    if isinstance(cleaned.get("properties"), dict):
        cleaned["properties"] = {
            name: clean_schema(value) for name, value in cleaned["properties"].items()
        }
    if isinstance(cleaned.get("items"), dict):
        cleaned["items"] = clean_schema(cleaned["items"])
    return cleaned


def declarations(tools: list[dict[str, Any]]) -> list[types.Tool]:
    if not tools:
        return []
    functions = [
        types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters_json_schema=clean_schema(tool["parameters"]),
        )
        for tool in tools
    ]
    return [types.Tool(function_declarations=functions)]


def tool_response(block: dict[str, Any]) -> dict[str, Any]:
    """Vosita natijasi (JSON matn yoki xato matni) → Gemini kutadigan obyekt."""
    content = block.get("content")
    if block.get("is_error"):
        return {"error": str(content or "")}
    try:
        return {"result": json.loads(content)} if isinstance(content, str) else {"result": content}
    except ValueError:
        return {"result": content}


def to_contents(messages: list[dict[str, Any]]) -> list[types.Content]:
    """Saqlangan tarix → Gemini `contents`. Avvalgi model (Claude) fikrlash bloklari tashlanadi;
    vosita natijasiga chaqiruvdagi nom va ID qo'yiladi."""
    calls: dict[str, tuple[str, str | None]] = {}
    contents: list[types.Content] = []
    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"
        parts: list[types.Part] = []
        for block in message["content"]:
            kind = block.get("type")
            if kind == "text" and block.get("text"):
                parts.append(types.Part(text=block["text"], thought_signature=decode(block)))
            elif kind == "tool_use":
                call_id = block.get("call_id") or None
                calls[str(block.get("id"))] = (block["name"], call_id)
                parts.append(
                    types.Part(
                        function_call=types.FunctionCall(
                            id=call_id, name=block["name"], args=block.get("input") or {}
                        ),
                        thought_signature=decode(block),
                    )
                )
            elif kind == "tool_result":
                name, call_id = calls.get(str(block.get("tool_use_id")), ("", None))
                parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=call_id,
                            name=name or str(block.get("name") or "tool"),
                            response=tool_response(block),
                        )
                    )
                )
        if not parts:
            continue
        if contents and contents[-1].role == role:
            (contents[-1].parts or []).extend(parts)
        else:
            contents.append(types.Content(role=role, parts=parts))
    return contents


# --- Gemini → Turn ---


@dataclass
class Collected:
    """Stream bo'laklaridan yig'ilgan javob: matn, vosita chaqiruvlari, imzolar va sarf."""

    model: str
    text: list[str] = field(default_factory=list)
    text_signature: bytes | None = None
    calls: list[tuple[types.FunctionCall, bytes | None]] = field(default_factory=list)
    finish: types.FinishReason | None = None
    blocked: bool = False
    usage: types.GenerateContentResponseUsageMetadata | None = None

    def add(self, chunk: types.GenerateContentResponse, on_text: Callable[[str], None]) -> None:
        if chunk.usage_metadata is not None:
            self.usage = chunk.usage_metadata
        if chunk.model_version:
            self.model = chunk.model_version
        feedback = chunk.prompt_feedback
        if feedback is not None and feedback.block_reason is not None:
            self.blocked = True
        for candidate in (chunk.candidates or [])[:1]:
            if candidate.finish_reason is not None:
                self.finish = candidate.finish_reason
            content = candidate.content
            for part in (content.parts if content is not None else None) or []:
                if part.function_call is not None:
                    self.calls.append((part.function_call, part.thought_signature))
                    continue
                if part.text and not part.thought:
                    self.text.append(part.text)
                    on_text(part.text)
                if part.thought_signature:
                    # Oddiy javobda imzo oxirgi qismda (ba'zan matni bo'sh qismda) keladi.
                    self.text_signature = part.thought_signature

    def stop_reason(self) -> str:
        if self.blocked or self.finish in REFUSALS:
            return "refusal"
        if self.finish == FinishReason.MAX_TOKENS:
            return "max_tokens"
        if self.finish not in (None, FinishReason.STOP):
            # Masalan, MALFORMED_FUNCTION_CALL: javob bo'sh bo'lsa, agent raqam so'raydi.
            logger.warning("Gemini javobi kutilmagan sabab bilan tugadi: %s", self.finish)
        return "tool_use" if self.calls else "end_turn"

    def turn(self) -> Turn:
        content: list[dict[str, Any]] = []
        text = "".join(self.text)
        if text:
            block: dict[str, Any] = {"type": "text", "text": text}
            if self.text_signature:
                block["signature"] = encode(self.text_signature)
            content.append(block)
        for call, signature in self.calls:
            item: dict[str, Any] = {
                "type": "tool_use",
                "id": call.id or f"gemini_{uuid.uuid4().hex[:12]}",
                "name": call.name or "",
                "input": dict(call.args or {}),
            }
            if call.id:
                item["call_id"] = call.id
            if signature:
                item["signature"] = encode(signature)
            content.append(item)
        meta = self.usage
        prompt = (meta.prompt_token_count or 0) if meta else 0
        cached = (meta.cached_content_token_count or 0) if meta else 0
        answer = (meta.candidates_token_count or 0) if meta else 0
        # Fikrlash tokenlari chiqish narxida hisoblanadi.
        thoughts = (meta.thoughts_token_count or 0) if meta else 0
        return Turn(
            content=content,
            stop_reason=self.stop_reason(),
            model=self.model,
            usage=Usage(
                input_tokens=max(0, prompt - cached),
                output_tokens=answer + thoughts,
                cache_read_tokens=cached,
            ),
        )


class GeminiModel:
    """Haqiqiy Gemini. Javob streaming bilan olinadi: matn kelishi bilan `on_text`ga beriladi."""

    def __init__(self, *, api_key: str, model: str, max_tokens: int, thinking: str) -> None:
        self.name = model
        self.max_tokens = max_tokens
        self.thinking = thinking if thinking in THINKING_LEVELS else "low"
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=RETRY_ATTEMPTS),
            ),
        )

    def config(
        self, system: str, tools: list[dict[str, Any]], allow_tools: bool
    ) -> types.GenerateContentConfig:
        modes = types.FunctionCallingConfigMode
        mode = modes.AUTO if allow_tools else modes.NONE
        return types.GenerateContentConfig(
            # Tizim prompti (kurslar, FAQ) hamma suhbatlar uchun bir xil — Gemini uni o'zi
            # keshlaydi (implicit caching): takroriy qism 10 barobar arzon.
            system_instruction=system,
            # Fikrlash tokenlari ham shu chegaraga kiradi: kichik qilinsa, javob kesilib qoladi.
            max_output_tokens=self.max_tokens,
            # Sotuv chati: tez va qisqa javob muhim — fikrlash chuqurligi past.
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel(self.thinking.upper())
            ),
            tools=[*declarations(tools)],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode=mode)
            ),
            # Vositalarni agent sikli o'zi bajaradi (tekshiruv, ariza, kartochkalar).
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
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
        collected = Collected(model=self.name)
        contents: list[types.ContentUnionDict] = [*to_contents(messages)]
        stream = self.client.models.generate_content_stream(
            model=self.name,
            contents=contents,
            config=self.config(system, tools, allow_tools),
        )
        for chunk in stream:
            collected.add(chunk, on_text)
        return collected.turn()
