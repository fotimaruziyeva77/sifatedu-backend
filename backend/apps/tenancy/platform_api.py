"""Platforma sayti API'si: tariflar, manzil tekshiruvi va markaz ochish arizasi."""

from typing import Any
from uuid import UUID

from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions, serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.request import get_client_ip
from apps.core.serializers import ReadOnlyModelSerializer
from apps.users import otp
from apps.users.models import OneTimeCode
from apps.users.serializers import CodeField, PhoneField, check_password
from apps.users.services import send_code_sms
from apps.users.views import CsrfProtectedView, OtpDailyLimit, invalid_code_error

from . import signup as flow
from .models import Plan, Signup
from .sections import Feature


class PublicPlanSerializer(ReadOnlyModelSerializer):
    features = serializers.ListField(child=serializers.ChoiceField(choices=Feature.choices))

    class Meta:
        model = Plan
        fields = (
            "id",
            "name",
            "price",
            "trial_days",
            "features",
            "max_students",
            "max_staff",
            "max_disk_gb",
        )


class AddressResultSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    reason = serializers.ChoiceField(choices=["free", "invalid", "reserved", "taken"])


class SignupSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.filter(is_public=True))
    name = serializers.CharField(min_length=2, max_length=200, trim_whitespace=True)
    slug = serializers.CharField(max_length=30)
    first_name = serializers.CharField(max_length=150, trim_whitespace=True)
    last_name = serializers.CharField(
        max_length=150, trim_whitespace=True, required=False, allow_blank=True
    )
    phone = PhoneField()
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate_name(self, value: str) -> str:
        if flow.NAME_FORBIDDEN.search(value):
            raise serializers.ValidationError(
                _("Nomda faqat harf, raqam, probel va oddiy tinish belgilari bo'lsin.")
            )
        return value

    def validate_slug(self, value: str) -> str:
        slug = value.lower()
        problem = flow.address_problem(slug)
        if problem == flow.Address.TAKEN:
            raise serializers.ValidationError(_("Bu manzil band."))
        if problem == flow.Address.RESERVED:
            raise serializers.ValidationError(_("Bu manzilni olib bo'lmaydi."))
        if problem:
            raise serializers.ValidationError(
                _("3–30 belgi: lotin harfi bilan boshlanadi, harf, raqam va chiziqcha.")
            )
        return slug

    def validate_password(self, value: str) -> str:
        return check_password(value)


class SignupStartedSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    resend_in = serializers.IntegerField()


class ResendSerializer(serializers.Serializer):
    resend_in = serializers.IntegerField()


class VerifySerializer(serializers.Serializer):
    code = CodeField()


class SignupStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Signup.Status.choices)
    url = serializers.CharField(allow_blank=True)


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT


class AddressConflict(Conflict):
    default_code = "address_taken"
    default_detail = _("Bu manzil hozirgina band bo'ldi. Boshqasini tanlang.")


class PhoneConflict(Conflict):
    default_code = "phone_taken"
    default_detail = _("Bu raqam bilan markaz allaqachon ochilgan.")


class SignupClosed(exceptions.APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "signup_closed"
    default_detail = _("Ro'yxatdan o'tish hozircha yopiq.")


def _require_open() -> None:
    if not settings.SIGNUP_OPEN:
        raise SignupClosed


def _pending(token: UUID) -> Signup:
    return get_object_or_404(Signup, token=token, status=Signup.Status.PENDING)


def _send_code(request: Request, phone: str) -> int:
    """Kod yuboradi. Oxirgi kod hali yangi bo'lsa, uni ishlatadi va qancha kutishni aytadi."""
    try:
        code = otp.issue_code(phone, OneTimeCode.Purpose.SIGNUP, get_client_ip(request))
    except otp.OtpCooldownError as exc:
        return exc.seconds
    except (otp.OtpDailyLimitError, otp.OtpQuotaError) as exc:
        raise OtpDailyLimit from exc
    send_code_sms(phone, code)
    return otp.RESEND_SECONDS


class PlansView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=PublicPlanSerializer(many=True), tags=["platform"])
    def get(self, request: Request) -> Response:
        plans = Plan.objects.filter(is_public=True)
        return Response(PublicPlanSerializer(plans, many=True).data)


class AddressView(APIView):
    """Forma yozilayotganda: manzil bo'shmi."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter("slug", str, required=True)],
        responses=AddressResultSerializer,
        tags=["platform"],
    )
    def get(self, request: Request) -> Response:
        problem = flow.address_problem(request.query_params.get("slug", "").lower())
        return Response({"available": problem is None, "reason": problem or "free"})


class SignupCreateView(CsrfProtectedView):
    throttle_scope = "signup"

    @extend_schema(
        request=SignupSerializer, responses={201: SignupStartedSerializer}, tags=["platform"]
    )
    def post(self, request: Request) -> Response:
        _require_open()
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data
        locale = (translation.get_language() or "uz")[:2]
        signup = flow.create_signup(**data, locale=locale)
        resend_in = _send_code(request, signup.phone)
        return Response(
            {"token": signup.token, "resend_in": resend_in}, status=status.HTTP_201_CREATED
        )


class SignupResendView(CsrfProtectedView):
    throttle_scope = "otp"

    @extend_schema(request=None, responses={200: ResendSerializer}, tags=["platform"])
    def post(self, request: Request, token: UUID) -> Response:
        _require_open()
        return Response({"resend_in": _send_code(request, _pending(token).phone)})


class SignupVerifyView(CsrfProtectedView):
    throttle_scope = "auth_verify"

    @extend_schema(
        request=VerifySerializer, responses={200: SignupStatusSerializer}, tags=["platform"]
    )
    def post(self, request: Request, token: UUID) -> Response:
        _require_open()
        signup = _pending(token)
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            otp.consume_code(
                signup.phone, OneTimeCode.Purpose.SIGNUP, serializer.validated_data["code"]
            )
        except otp.InvalidCodeError as exc:
            raise invalid_code_error() from exc
        try:
            flow.confirm(signup)
        except flow.PhoneTaken as exc:
            raise PhoneConflict from exc
        except flow.AddressTaken as exc:
            raise AddressConflict from exc
        return Response({"status": signup.status, "url": ""})


class SignupStatusView(APIView):
    """«Tayyorlanmoqda» ekrani shu holatni so'rab turadi. Token ariza egasida."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=SignupStatusSerializer, tags=["platform"])
    def get(self, request: Request, token: UUID) -> Response:
        signup = get_object_or_404(Signup, token=token)
        url = flow.ready_url(signup) if signup.status == Signup.Status.READY else ""
        return Response({"status": signup.status, "url": url})
