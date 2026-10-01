from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Conversation


class ChatCardSerializer(serializers.Serializer[dict[str, Any]]):
    """Chatdagi kurs kartochkasi (AI `show_courses` bilan ko'rsatgan)."""

    slug = serializers.CharField()
    title = serializers.CharField()
    icon = serializers.CharField()
    audience = serializers.CharField()
    age_min = serializers.IntegerField(allow_null=True)
    age_max = serializers.IntegerField(allow_null=True)
    study_format = serializers.CharField()
    is_free = serializers.BooleanField()
    price_online = serializers.IntegerField()
    price_offline_monthly = serializers.IntegerField()
    duration_hours = serializers.IntegerField(allow_null=True)
    lesson_count = serializers.IntegerField()


class ChatMessageSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=["user", "assistant"])
    text = serializers.CharField(allow_blank=True)
    attachments = ChatCardSerializer(many=True)
    rating = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField()


class ChatConversationSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Conversation.Status.choices)
    pending = serializers.BooleanField(
        help_text="Javob hali tayyorlanyapti: sayt so'rashda davom etadi."
    )
    has_lead = serializers.BooleanField()


class ChatStateSerializer(serializers.Serializer[dict[str, Any]]):
    conversation = ChatConversationSerializer(allow_null=True)
    messages = ChatMessageSerializer(many=True)
    draft = serializers.CharField(
        allow_blank=True, help_text="Yozilayotgan javobning hozircha tayyor qismi."
    )


class QuizContextSerializer(serializers.Serializer[dict[str, Any]]):
    """Kasb testi natijasi: AI maslahatni shunga qarab beradi."""

    track = serializers.CharField(max_length=60, required=False, allow_blank=True)
    level = serializers.CharField(max_length=60, required=False, allow_blank=True)
    hours = serializers.CharField(max_length=30, required=False, allow_blank=True)
    course = serializers.CharField(max_length=200, required=False, allow_blank=True)


class ChatSendSerializer(serializers.Serializer[dict[str, Any]]):
    text = serializers.CharField(max_length=1000, trim_whitespace=True)
    page = serializers.CharField(max_length=500, required=False, allow_blank=True)
    quiz = QuizContextSerializer(required=False)

    def validate_text(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError(_("Xabar bo'sh."))
        return value


class ChatRateSerializer(serializers.Serializer[dict[str, Any]]):
    message = serializers.IntegerField()
    rating = serializers.ChoiceField(
        choices=[1, -1, 0], help_text="1 — 👍, -1 — 👎, 0 — bekor qilish"
    )
