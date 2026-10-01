import json
from typing import Any

from rest_framework import serializers

from .models import Question

MAX_RESPONSE_CHARS = 5000


class QuizOptionSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    text = serializers.CharField()


class QuizQuestionSerializer(serializers.Serializer[dict[str, Any]]):
    """Savol javobsiz: `options` — tanlash, `items` — tartiblash, `left`/`right` — juftlash.
    Variant `id` si — shu urinishdagi ekrandagi o'rni (1 dan), javobda aynan shu ishlatiladi."""

    id = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=Question.Kind.choices)
    text = serializers.CharField()
    code = serializers.CharField(allow_blank=True)
    language = serializers.CharField(allow_blank=True)
    options = QuizOptionSerializer(many=True)
    items = QuizOptionSerializer(many=True)
    left = QuizOptionSerializer(many=True)
    right = QuizOptionSerializer(many=True)


class QuizResultSerializer(serializers.Serializer[dict[str, Any]]):
    question = serializers.IntegerField()
    correct = serializers.BooleanField()
    response = serializers.DictField(help_text="O'quvchining javobi (so'rovdagi format).")
    correct_answer = serializers.DictField(
        allow_null=True,
        help_text="To'g'ri javob (xuddi shu formatda) — faqat test o'tilgach, aks holda null.",
    )
    explanation = serializers.CharField(allow_blank=True, help_text="Izoh — faqat test o'tilgach.")


class QuizAttemptSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    quiz_id = serializers.IntegerField()
    title = serializers.CharField()
    pass_percent = serializers.IntegerField()
    total = serializers.IntegerField()
    questions = QuizQuestionSerializer(many=True)
    answers = QuizResultSerializer(many=True, help_text="Berilgan javoblar (davom ettirishda).")


class QuizAnswerSerializer(serializers.Serializer[dict[str, Any]]):
    """`response`: {"choice": id} | {"choices": [..]} | {"text": ".."} | {"order": [..]} |
    {"pairs": {"chap_id": o'ng_id}} — ID lar savoldagi variantlarniki."""

    question = serializers.IntegerField()
    response = serializers.DictField()

    def validate_response(self, value: dict[str, Any]) -> dict[str, Any]:
        # Javob bazaga yoziladi: haddan tashqari katta ma'lumot qabul qilinmaydi.
        if len(json.dumps(value, ensure_ascii=False)) > MAX_RESPONSE_CHARS:
            raise serializers.ValidationError("Javob juda uzun.")
        return value


class QuizFinishSerializer(serializers.Serializer[dict[str, Any]]):
    score = serializers.IntegerField()
    stars = serializers.IntegerField()
    passed = serializers.BooleanField()
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    best_score = serializers.IntegerField()
    best_stars = serializers.IntegerField()
    review = QuizResultSerializer(
        many=True, help_text="Test o'tilgan bo'lsa: har savol bo'yicha to'g'ri javob va izoh."
    )


class QuizSummarySerializer(serializers.Serializer[dict[str, Any]]):
    """Dars sahifasidagi test kartasi."""

    id = serializers.IntegerField()
    title = serializers.CharField()
    questions = serializers.IntegerField()
    pass_percent = serializers.IntegerField()
    best_score = serializers.IntegerField(allow_null=True)
    stars = serializers.IntegerField()
    passed = serializers.BooleanField()
    attempts = serializers.IntegerField()
    in_progress = serializers.BooleanField(help_text="Boshlangan, lekin yakunlanmagan urinish bor.")
    telegram = serializers.BooleanField(help_text="Testni Telegram botda ishlash mumkin.")
