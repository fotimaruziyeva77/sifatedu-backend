"""Markaz sozlamalari: maxfiy qiymatlar faqat kiritiladi, hech qachon qaytarilmaydi."""

from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.content.models import HEX_COLOR, LOGO_MAX_MB
from apps.tenancy.signup import NAME_FORBIDDEN

LOGO_MAX_BYTES = LOGO_MAX_MB * 1024 * 1024
LOGO_FORMATS = {"JPEG", "PNG", "WEBP"}


class TelegramStateSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    connected = serializers.BooleanField()
    username = serializers.CharField(allow_blank=True)
    login = serializers.BooleanField()
    leads_chat = serializers.CharField(allow_blank=True)
    reports_chat = serializers.CharField(allow_blank=True)


class ClickStateSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    connected = serializers.BooleanField()
    service_id = serializers.CharField(allow_blank=True)
    merchant_id = serializers.CharField(allow_blank=True)
    merchant_user_id = serializers.CharField(allow_blank=True)
    tin = serializers.CharField(allow_blank=True)
    prepare_url = serializers.CharField()
    complete_url = serializers.CharField()


class EskizStateSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    connected = serializers.BooleanField()
    email = serializers.CharField(allow_blank=True)
    sender = serializers.CharField(allow_blank=True)


class StepsSerializer(serializers.Serializer):
    brand = serializers.BooleanField()
    course = serializers.BooleanField()
    group = serializers.BooleanField()
    legal = serializers.BooleanField()


class AdminLinksSerializer(serializers.Serializer):
    course_add = serializers.CharField()
    group_add = serializers.CharField()
    site = serializers.CharField()
    legal = serializers.CharField()


class CenterSetupSerializer(serializers.Serializer):
    name = serializers.CharField()
    address = serializers.CharField()
    color = serializers.CharField(allow_blank=True)
    logo = serializers.CharField(allow_blank=True)
    logo_dark = serializers.CharField(allow_blank=True)
    steps = StepsSerializer()
    admin = AdminLinksSerializer()
    telegram = TelegramStateSerializer()
    click = ClickStateSerializer()
    eskiz = EskizStateSerializer()


def _checked_logo(file: UploadedFile | None) -> UploadedFile | None:
    if file is None:
        return None
    image_format = getattr(getattr(file, "image", None), "format", None)
    if image_format not in LOGO_FORMATS:
        raise serializers.ValidationError(_("Faqat PNG, JPG yoki WebP."))
    if file.size is not None and file.size > LOGO_MAX_BYTES:
        raise serializers.ValidationError(_("Rasm hajmi 2 MB dan oshmasin."))
    return file


class BrandSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=200, required=False)
    color = serializers.RegexField(rf"{HEX_COLOR}|^$", required=False, allow_blank=True)
    logo = serializers.ImageField(required=False, allow_null=True)
    logo_dark = serializers.ImageField(required=False, allow_null=True)

    def validate_name(self, value: str) -> str:
        if NAME_FORBIDDEN.search(value):
            raise serializers.ValidationError(
                _("Nomda faqat harf, raqam, probel va oddiy tinish belgilari bo'lsin.")
            )
        return value

    def validate_logo(self, value: UploadedFile | None) -> UploadedFile | None:
        return _checked_logo(value)

    def validate_logo_dark(self, value: UploadedFile | None) -> UploadedFile | None:
        return _checked_logo(value)


class TelegramConnectSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128, write_only=True)


class TelegramOptionsSerializer(serializers.Serializer):
    leads_chat = serializers.CharField(max_length=32, required=False, allow_blank=True)
    reports_chat = serializers.CharField(max_length=32, required=False, allow_blank=True)
    login = serializers.BooleanField(required=False)


class ClickSerializer(serializers.Serializer):
    service_id = serializers.CharField(max_length=32)
    merchant_id = serializers.CharField(max_length=32)
    merchant_user_id = serializers.CharField(max_length=32, required=False, allow_blank=True)
    tin = serializers.CharField(max_length=20, required=False, allow_blank=True)
    secret_key = serializers.CharField(
        max_length=128, write_only=True, required=False, allow_blank=True
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs.get("secret_key") and not self.context["has_secret"]:
            raise serializers.ValidationError({"secret_key": [_("Maxfiy kalitni kiriting.")]})
        return attrs


class EskizSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, write_only=True)
    sender = serializers.CharField(max_length=20, required=False, allow_blank=True)
