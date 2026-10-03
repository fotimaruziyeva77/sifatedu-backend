"""Agent sikli: mijozning oxirgi xabariga javob.

Bitta javob — bir necha "qadam": model matn yozadi yoki vosita chaqiradi, vosita natijasi modelga
qaytadi va u yakuniy javobni yozadi (ko'pi bilan `MAX_STEPS`). Har bir qadam `Message` bo'lib
saqlanadi: keyingi xabarlarda tarix aynan shu ko'rinishda yuboriladi va keshdan o'qiladi.
"""

import logging
import time
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone
from google.genai import errors as gemini_errors

from apps.notifications.alerts import alert

from . import budget
from .llm import ChatModel, GeminiModel, Turn, cost_usd
from .models import AssistantSettings, Conversation, Message
from .phones import unmask
from .prompt import build_system_prompt
from .rules import PHRASES, RuleModel
from .tools import MAX_CARDS, TOOLS, run_tool

logger = logging.getLogger(__name__)

MAX_STEPS = 4
PARTIAL_TTL_SECONDS = 120
# Qayta urinish foyda bermaydigan xatolar: so'rov shakli, kalit, ruxsat yoki model nomi noto'g'ri.
NOT_RETRYABLE = (400, 401, 403, 404)
PARTIAL_INTERVAL_SECONDS = 0.15


def partial_key(conversation_id: int) -> str:
    return f"assistant:partial:{conversation_id}"


class PartialText:
    """Yozilayotgan javob Redis'da: sayt uni so'rab turadi va matn asta-sekin paydo bo'ladi."""

    def __init__(self, conversation_id: int) -> None:
        self.key = partial_key(conversation_id)
        self.text = ""
        self.saved_at = 0.0

    def add(self, delta: str) -> None:
        self.text += delta
        now = time.monotonic()
        if now - self.saved_at >= PARTIAL_INTERVAL_SECONDS:
            cache.set(self.key, self.text, PARTIAL_TTL_SECONDS)
            self.saved_at = now

    def paragraph(self) -> None:
        if self.text and not self.text.endswith("\n\n"):
            self.text += "\n\n"

    def clear(self) -> None:
        cache.delete(self.key)


def ai_configured() -> bool:
    """Saytdagi chat ko'rsatiladimi: Gemini kaliti bor yoki test rejimi yoqilgan."""
    return bool(settings.GEMINI_API_KEY) or settings.ASSISTANT_DRY_RUN


def choose_model(conversation: Conversation, config: AssistantSettings) -> ChatModel:
    # Test rejimi kalitdan ustun: kalit `.env`da tursa ham E2E va local sinov pul sarflamaydi.
    if settings.ASSISTANT_DRY_RUN or not settings.GEMINI_API_KEY:
        return RuleModel(locale=conversation.locale, dry_run=settings.ASSISTANT_DRY_RUN)
    if (
        not config.enabled
        or conversation.user_messages > config.max_user_messages
        or not budget.within_budget(config)
    ):
        # AI to'xtatilgan, limit yoki budjet tugagan: mijoz baribir raqam qoldira oladi.
        return RuleModel(locale=conversation.locale, dry_run=False)
    return GeminiModel(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        max_tokens=settings.ASSISTANT_MAX_TOKENS,
        thinking=settings.GEMINI_THINKING_LEVEL,
    )


def api_history(conversation: Conversation) -> list[dict[str, Any]]:
    """Saqlangan xabarlardan model tarixi. Buzilgan joylar (javobsiz vosita chaqiruvi,
    ketma-ket bir xil rol) API qabul qiladigan ko'rinishga keltiriladi."""
    items = list(conversation.messages.order_by("id").values_list("role", "content"))
    history: list[dict[str, Any]] = []
    for index, (role, content) in enumerate(items):
        blocks = [dict(block) for block in content or []]
        if role == Message.Role.ASSISTANT:
            answered = index + 1 < len(items) and items[index + 1][0] == Message.Role.TOOL
            if not answered:
                blocks = [block for block in blocks if block.get("type") != "tool_use"]
            # Faqat fikrlashdan iborat qolgan javob (matn ham, vosita ham yo'q) — yuborilmaydi.
            if not any(block.get("type") in ("text", "tool_use") for block in blocks):
                continue
        api_role = "assistant" if role == Message.Role.ASSISTANT else "user"
        if not blocks or (not history and api_role == "assistant"):
            continue
        if history and history[-1]["role"] == api_role:
            history[-1]["content"].extend(blocks)
        else:
            history.append({"role": api_role, "content": blocks})
    return history


def _save_turn(conversation: Conversation, turn: Turn, latency_ms: int) -> Message:
    cost = cost_usd(turn.usage)
    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        text=unmask(turn.text, conversation.phones),
        content=turn.content,
        model=turn.model,
        input_tokens=turn.usage.input_tokens,
        output_tokens=turn.usage.output_tokens,
        cache_read_tokens=turn.usage.cache_read_tokens,
        cache_write_tokens=turn.usage.cache_write_tokens,
        cost_usd=cost,
        latency_ms=latency_ms,
    )
    if cost:
        Conversation.objects.filter(pk=conversation.pk).update(cost_usd=F("cost_usd") + cost)
    return message


def _run(
    conversation: Conversation,
    model: ChatModel,
    system: str,
    history: list[dict[str, Any]],
    partial: PartialText,
) -> tuple[list[Message], list[dict[str, Any]]]:
    created: list[Message] = []
    cards: list[dict[str, Any]] = []
    for step in range(MAX_STEPS):
        allow_tools = step < MAX_STEPS - 1
        started = time.monotonic()
        try:
            turn = model.respond(
                system=system,
                tools=TOOLS,
                messages=history,
                allow_tools=allow_tools,
                on_text=partial.add,
            )
        except (gemini_errors.APIError, httpx.HTTPError, ValueError) as exc:
            # ValueError — javob o'qilmadi (SDK tekshiruvi). Sozlama yoki kod xatosi (kalit,
            # model nomi, so'rov shakli) Sentry'ga tushadi; tarmoq, limit va server xatolari
            # SDK qayta urinishlaridan keyin ham — ogohlantirish.
            fatal = isinstance(exc, gemini_errors.APIError) and exc.code in NOT_RETRYABLE
            logger.log(logging.ERROR if fatal else logging.WARNING, "Gemini API xatosi: %s", exc)
            alert(
                "assistant:api", f"Gemini API xatosi: {type(exc).__name__}. Oddiy rejim ishlayapti."
            )
            model = RuleModel(locale=conversation.locale, dry_run=False)
            turn = model.respond(
                system=system,
                tools=TOOLS,
                messages=history,
                allow_tools=allow_tools,
                on_text=partial.add,
            )
        created.append(_save_turn(conversation, turn, int((time.monotonic() - started) * 1000)))
        history.append({"role": "assistant", "content": turn.content})

        calls = turn.tool_calls
        # Faqat "tool_use" bilan tugagan javobdagi vositalar bajariladi: `max_tokens` yoki
        # `refusal` bilan kesilgan javobdagi chaqiruv to'liq bo'lmasligi mumkin.
        if turn.stop_reason != "tool_use" or not calls:
            if turn.stop_reason == "refusal":
                logger.info("Gemini javobni rad etdi: suhbat #%s", conversation.pk)
            break
        results = []
        for call in calls:
            outcome = run_tool(conversation, call.name, call.input)
            cards.extend(outcome.attachments)
            block: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": call.id,
                "name": call.name,
                "content": outcome.content,
            }
            if outcome.is_error:
                block["is_error"] = True
            results.append(block)
        Message.objects.create(conversation=conversation, role=Message.Role.TOOL, content=results)
        history.append({"role": "user", "content": results})
        partial.paragraph()
    return created, cards


def _fallback_message(conversation: Conversation) -> Message:
    text = PHRASES.get(conversation.locale, PHRASES["uz"])["ask_phone"]
    return Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        text=text,
        content=[{"type": "text", "text": text}],
        model="fallback",
    )


def respond(conversation: Conversation) -> list[Message]:
    """Oxirgi mijoz xabariga javob beradi va yaratilgan AI xabarlarini qaytaradi."""
    config = AssistantSettings.load()
    model = choose_model(conversation, config)
    system = build_system_prompt(conversation.locale, config)
    partial = PartialText(conversation.pk)
    try:
        created, cards = _run(conversation, model, system, api_history(conversation), partial)
    except Exception:
        # Kutilmagan xato: mijoz javobsiz qolmasin — raqam qoldirishni taklif qilamiz.
        logger.exception("AI javobi tayyorlanmadi: suhbat #%s", conversation.pk)
        alert("assistant:error", f"AI javobi tayyorlanmadi (suhbat #{conversation.pk}).")
        created, cards = [_fallback_message(conversation)], []
    finally:
        partial.clear()

    if not cards and not any(message.text for message in created):
        # Bo'sh yoki rad etilgan javob: mijoz jim qolgan chatni ko'rmasin.
        created.append(_fallback_message(conversation))

    if cards and created:
        visible = [message for message in created if message.text] or created
        target = visible[-1]
        unique = {card["slug"]: card for card in cards}
        target.attachments = list(unique.values())[:MAX_CARDS]
        target.save(update_fields=["attachments"])
    Conversation.objects.filter(pk=conversation.pk).update(last_message_at=timezone.now())
    if isinstance(model, GeminiModel):
        budget.check_warning(config)
    return created
