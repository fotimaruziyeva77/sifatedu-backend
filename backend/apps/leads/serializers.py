from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.catalog.models import Course
from apps.core.phone import InvalidPhoneError, normalize_phone


class LeadCreateSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=100, trim_whitespace=True)
    phone = serializers.CharField(max_length=32)
    course: "serializers.SlugRelatedField[Course]" = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Course.objects.filter(status=Course.Status.PUBLISHED),
        required=False,
        allow_null=True,
    )
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    source_page = serializers.CharField(max_length=500, required=False, allow_blank=True)
    utm_source = serializers.CharField(max_length=200, required=False, allow_blank=True)
    utm_medium = serializers.CharField(max_length=200, required=False, allow_blank=True)
    utm_campaign = serializers.CharField(max_length=200, required=False, allow_blank=True)
    utm_term = serializers.CharField(max_length=200, required=False, allow_blank=True)
    utm_content = serializers.CharField(max_length=200, required=False, allow_blank=True)
    # Honeypot: foydalanuvchiga ko'rinmaydi, botlar to'ldiradi.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_phone(self, value: str) -> str:
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise serializers.ValidationError(
                _("Telefon raqami +998XXXXXXXXX formatida bo'lishi kerak."), code="invalid_phone"
            ) from exc


class LeadAcceptedSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok"])
