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


# --- Qo'llanmadan AI test (o'qituvchi) ---


class QuizDraftSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=["PENDING", "READY", "FAILED", "PUBLISHED"],
        help_text="PENDING — AI tuzmoqda, READY — tekshirishga tayyor, FAILED — xato, "
        "PUBLISHED — e'lon qilingan.",
    )
    lesson_id = serializers.IntegerField(help_text="Mavzu — kurs darsi.")
    lesson_title = serializers.CharField()
    file_name = serializers.CharField()
    text = serializers.CharField(allow_blank=True, help_text="Savollar «Tez kiritish» formatida.")
    error = serializers.CharField(allow_blank=True)
    count = serializers.IntegerField(help_text="E'lon qilingan savollar soni.")
    created_at = serializers.DateTimeField()


class QuizDraftCreateSerializer(serializers.Serializer[dict[str, Any]]):
    file = serializers.FileField(help_text="Qo'llanma: PDF, Word, PowerPoint, rasm yoki matn.")
    lesson = serializers.IntegerField(
        required=False, allow_null=True, help_text="Mavzu (kurs darsi); bo'lmasa — new_title."
    )
    new_title = serializers.CharField(
        required=False, allow_blank=True, max_length=200, help_text="Yangi mavzu nomi."
    )


class QuizDraftPublishSerializer(serializers.Serializer[dict[str, Any]]):
    text = serializers.CharField(max_length=100_000, help_text="Tuzatilgan savollar matni.")
    share_file = serializers.BooleanField(
        default=False, help_text="Qo'llanma o'quvchilarga dars materiali bo'lib qo'shilsin."
    )


class QuizDraftPublishedSerializer(serializers.Serializer[dict[str, Any]]):
    draft = QuizDraftSerializer()
    count = serializers.IntegerField(help_text="Testga qo'shilgan savollar.")
    covered = serializers.BooleanField(
        help_text="Mavzu guruhda ochiq — o'quvchilar testni hozir ishlay oladi."
    )
    notified = serializers.BooleanField(
        help_text="O'quvchilarga hozir «Dars ochildi · Testni boshlash» xabari ketdi."
    )
