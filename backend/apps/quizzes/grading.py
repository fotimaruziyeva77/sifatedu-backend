"""Savollarni baholash, to'g'ri javobni ko'rsatish va variantlar to'g'riligini tekshirish.

Javob formatlari (bu yerda — variantlarning baza ID lari; brauzer o'rinlar bilan yuboradi,
tarjimasi — services.Layout):
  SINGLE   — {"choice": id}
  MULTIPLE — {"choices": [id, ...]}
  TEXT     — {"text": "..."}
  ORDER    — {"order": [id, ...]}           (qadamlar o'quvchi qo'ygan tartibda)
  MATCH    — {"pairs": {"chap_id": o'ng_id}} (o'ng tomon ham variant ID si bilan)
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .models import Choice, Question

Kind = Question.Kind


def normalize(value: str) -> str:
    """Matn javob: katta-kichik harf, ortiqcha bo'shliq va oxirgi tinish belgisi farq qilmaydi."""
    return " ".join(str(value).lower().split()).strip(" .!?,;:")


def correct_order(choices: Sequence[Choice]) -> list[int]:
    return [choice.pk for choice in sorted(choices, key=lambda item: (item.order, item.pk))]


def grade(question: Question, choices: Sequence[Choice], response: dict[str, Any]) -> bool:
    kind = question.kind
    if kind == Kind.SINGLE:
        chosen = response.get("choice")
        return any(choice.pk == chosen and choice.is_correct for choice in choices)
    if kind == Kind.MULTIPLE:
        picked = response.get("choices")
        if not isinstance(picked, list):
            return False
        return set(picked) == {choice.pk for choice in choices if choice.is_correct}
    if kind == Kind.TEXT:
        answer = normalize(str(response.get("text", "")))
        return bool(answer) and answer in {normalize(choice.text) for choice in choices}
    if kind == Kind.ORDER:
        return response.get("order") == correct_order(choices)
    if kind == Kind.MATCH:
        pairs = response.get("pairs")
        if not isinstance(pairs, dict):
            return False
        return len(pairs) == len(choices) and all(
            pairs.get(str(choice.pk)) == choice.pk for choice in choices
        )
    return False


def correct_answer(question: Question, choices: Sequence[Choice]) -> dict[str, Any]:
    """Javobdan keyin ko'rsatiladigan to'g'ri javob (javob bilan bir xil formatda)."""
    kind = question.kind
    if kind in (Kind.SINGLE, Kind.MULTIPLE):
        return {"choices": [choice.pk for choice in choices if choice.is_correct]}
    if kind == Kind.TEXT:
        return {"text": choices[0].text if choices else ""}
    if kind == Kind.ORDER:
        return {"order": correct_order(choices)}
    return {"pairs": {str(choice.pk): choice.pk for choice in choices}}


@dataclass(frozen=True)
class DraftChoice:
    text: str
    is_correct: bool = False
    match: str = ""


def problems(kind: str, choices: Sequence[DraftChoice]) -> list[str]:
    """Savol ishlashi uchun variantlar yetarlimi. Bo'sh ro'yxat — hammasi joyida."""
    correct = sum(1 for choice in choices if choice.is_correct)
    if kind == Kind.SINGLE:
        if len(choices) < 2:
            return ["Kamida 2 ta variant kerak."]
        if correct != 1:
            return ["Bitta to'g'ri javobli savolda aynan 1 ta variant to'g'ri bo'lishi kerak."]
    elif kind == Kind.MULTIPLE:
        if len(choices) < 2:
            return ["Kamida 2 ta variant kerak."]
        if correct < 1:
            return ["Kamida 1 ta variant to'g'ri bo'lishi kerak."]
    elif kind == Kind.TEXT:
        if not choices:
            return ["Kamida 1 ta qabul qilinadigan javob kerak."]
    elif kind == Kind.ORDER:
        if len(choices) < 2:
            return ["Tartiblash uchun kamida 2 ta qadam kerak."]
    elif kind == Kind.MATCH:
        if len(choices) < 2:
            return ["Moslashtirish uchun kamida 2 ta juft kerak."]
        if any(not choice.match.strip() for choice in choices):
            return ["Har bir juftning o'ng tomoni to'ldirilishi kerak."]
    return []
