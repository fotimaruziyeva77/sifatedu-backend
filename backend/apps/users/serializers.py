from typing import Any

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.phone import InvalidPhoneError, normalize_phone

from .models import OneTimeCode, User
from .roles import Role, role_names

AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_FORMATS = {"JPEG", "PNG", "WEBP"}


class PhoneField(serializers.CharField):
    """Har qanday yozuvdagi o'zbek raqamini `+998XXXXXXXXX` ko'rinishiga keltiradi."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 32)
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        try:
            return normalize_phone(value)
        except InvalidPhoneError as exc:
            raise serializers.ValidationError(
                _("Telefon raqami +998XXXXXXXXX formatida bo'lishi kerak."), code="invalid_phone"
            ) from exc


class CodeField(serializers.RegexField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            r"^\d{6}$",
            error_messages={"invalid": _("Kod 6 ta raqamdan iborat.")},
            **kwargs,
        )


def check_password(password: str, user: User | None = None) -> str:
    """Django parol qoidalari (uzunlik, oddiy parollar, faqat raqamlar, shaxsiy ma'lumotga
    o'xshashlik). Xabarlar so'rov tilida."""
    try:
        password_validation.validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return password


class OtpRequestSerializer(serializers.Serializer):
    phone = PhoneField()
    purpose = serializers.ChoiceField(choices=OneTimeCode.Purpose.choices)


class OtpSentSerializer(serializers.Serializer):
    """Kod yuborildi: keyingi kodni necha soniyadan so'ng so'rash mumkin."""

    resend_in = serializers.IntegerField()


class RegisterSerializer(serializers.Serializer):
    phone = PhoneField()
    code = CodeField()
    first_name = serializers.CharField(max_length=150, trim_whitespace=True)
    last_name = serializers.CharField(
        max_length=150, trim_whitespace=True, required=False, allow_blank=True
    )
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    accept_terms = serializers.BooleanField()
    # Aksiya va yangiliklar Telegram/SMS orqali — faqat rozilik bilan (oldindan belgilanmagan).
    marketing_consent = serializers.BooleanField(required=False, default=False)

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                _("Davom etish uchun oferta va maxfiylik siyosatiga rozilik kerak."),
                code="terms_required",
            )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Parol ism va telefonga o'xshamasligi tekshiriladi (UserAttributeSimilarityValidator).
        draft = User(
            phone=attrs["phone"],
            first_name=attrs["first_name"],
            last_name=attrs.get("last_name", ""),
        )
        try:
            check_password(attrs["password"], draft)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail}) from exc
        return attrs


class LoginSerializer(serializers.Serializer):
    phone = PhoneField()
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)


class PasswordResetSerializer(serializers.Serializer):
    phone = PhoneField()
    code = CodeField()
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate_current_password(self, value: str) -> str:
        user: User = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Joriy parol noto'g'ri."), code="wrong_password")
        return value

    def validate_password(self, value: str) -> str:
        return check_password(value, self.context["request"].user)


class MeSerializer(serializers.ModelSerializer):
    """Joriy foydalanuvchi. Rasmni o'chirish uchun `avatar: null` yuboriladi."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)
    locale = serializers.ChoiceField(choices=settings.LANGUAGES, required=False)
    avatar = serializers.ImageField(required=False, allow_null=True)
    roles = serializers.SerializerMethodField(help_text="Kabinet menyusi rolga qarab (roles.py).")
    unread_notifications = serializers.SerializerMethodField(
        help_text="Kabinetdagi o'qilmagan xabarlar soni (menyudagi belgi)."
    )
    pending_reviews = serializers.SerializerMethodField(
        help_text="O'qituvchi tekshirishi kerak bo'lgan uy vazifalari (boshqalarga 0)."
    )
    has_schedule = serializers.SerializerMethodField(
        help_text="Jonli darslar jadvali bor: guruhda o'qiydi yoki guruhga dars beradi."
    )

    class Meta:
        model = User
        fields = (
            "phone",
            "first_name",
            "last_name",
            "full_name",
            "locale",
            "avatar",
            # Kabinet ko'rinishi: kattalar yoki bolalar (SIFAT Kids).
            "audience",
            "date_joined",
            "is_staff",
            "roles",
            "unread_notifications",
            "pending_reviews",
            "has_schedule",
        )
        read_only_fields = (
            "phone",
            "full_name",
            "date_joined",
            "is_staff",
            "roles",
            "unread_notifications",
            "pending_reviews",
            "has_schedule",
        )
        extra_kwargs = {
            "first_name": {"max_length": 150},
            "last_name": {"max_length": 150},
        }

    @extend_schema_field(serializers.ListField(child=serializers.ChoiceField(choices=Role.choices)))
    def get_roles(self, obj: User) -> list[str]:
        names = role_names(obj)
        return [role for role in Role.values if role in names]

    def get_unread_notifications(self, obj: User) -> int:
        return obj.notifications.filter(read_at__isnull=True).count()

    def get_pending_reviews(self, obj: User) -> int:
        from apps.homework.services import pending_reviews

        return pending_reviews(obj)

    def get_has_schedule(self, obj: User) -> bool:
        from apps.live.services import has_schedule

        return has_schedule(obj)

    def validate_first_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError(_("Ismingizni kiriting."), code="required")
        return value.strip()

    def validate_avatar(self, value: UploadedFile | None) -> UploadedFile | None:
        if value is None:
            return value
        if value.size and value.size > AVATAR_MAX_BYTES:
            raise serializers.ValidationError(
                _("Rasm hajmi 2 MB dan oshmasin."), code="file_too_large"
            )
        # ImageField Pillow bilan tekshirgan: formatni ham cheklaymiz (GIF, BMP va h.k. emas).
        image = getattr(value, "image", None)
        if image is not None and image.format not in AVATAR_FORMATS:
            raise serializers.ValidationError(
                _("Rasm JPG, PNG yoki WebP formatida bo'lsin."), code="invalid_format"
            )
        return value

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        # Eski rasm faylini storage'dan o'chiramiz: yetim fayllar yig'ilmasin.
        if "avatar" in validated_data and instance.avatar:
            new = validated_data["avatar"]
            if new is None or new != instance.avatar:
                instance.avatar.delete(save=False)
        if validated_data.get("avatar", ...) is None:
            validated_data["avatar"] = ""
        return super().update(instance, validated_data)


class GoogleLoginSerializer(serializers.Serializer):
    """Google Identity Services bergan ID token."""

    credential = serializers.CharField(max_length=4096, trim_whitespace=True)


class TelegramLoginSerializer(serializers.Serializer):
    """Telegram Login Widget qaytargan maydonlar (hammasi imzoga kiradi)."""

    id = serializers.CharField(max_length=32)
    auth_date = serializers.CharField(max_length=20)
    hash = serializers.CharField(max_length=128)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    photo_url = serializers.URLField(required=False, allow_blank=True)


class SocialPhoneSerializer(serializers.Serializer):
    """Ijtimoiy kirishdan keyingi telefon qadami. Raqam band bo'lsa, `code` ham kerak."""

    phone = PhoneField()
    code = CodeField(required=False)
    marketing_consent = serializers.BooleanField(required=False, default=False)


class SocialResultSerializer(serializers.Serializer):
    """`ok` — kirdi; `phone_required` — telefon so'raladi;
    `code_required` — raqam band, SMS kod kerak."""

    status = serializers.ChoiceField(choices=["ok", "phone_required", "code_required"])
    user = MeSerializer(required=False)
    first_name = serializers.CharField(required=False)


class SocialProvidersSerializer(serializers.Serializer):
    """Frontend qaysi tugmalarni ko'rsatishini bilishi uchun."""

    google_client_id = serializers.CharField(allow_blank=True)
    telegram_bot = serializers.CharField(allow_blank=True)
