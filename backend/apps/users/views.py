"""Auth va profil API'si: Django session + CSRF."""

from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.request import get_client_ip

from . import otp, services
from .models import OneTimeCode, User
from .serializers import (
    GoogleLoginSerializer,
    LoginSerializer,
    MeSerializer,
    OtpRequestSerializer,
    OtpSentSerializer,
    PasswordChangeSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    SocialPhoneSerializer,
    SocialProvidersSerializer,
    SocialResultSerializer,
    TelegramLoginSerializer,
    check_password,
)
from .social import (
    SocialAuthError,
    SocialProfile,
    google_enabled,
    telegram_enabled,
    verify_google,
    verify_telegram,
)


class OtpCooldown(exceptions.Throttled):
    default_detail = _("Kod yaqinda yuborilgan. Birozdan so'ng qayta so'rang.")
    default_code = "otp_cooldown"


class OtpDailyLimit(exceptions.Throttled):
    default_detail = _("Bugun bu raqamga juda ko'p kod yuborildi. Ertaga qayta urinib ko'ring.")
    default_code = "otp_daily_limit"


class LoginLocked(exceptions.Throttled):
    default_detail = _(
        "Juda ko'p noto'g'ri urinish. 15 daqiqadan so'ng qayta urinib ko'ring yoki parolni tiklang."
    )
    default_code = "login_locked"


def phone_taken_error() -> serializers.ValidationError:
    return serializers.ValidationError(
        {"phone": [_("Bu raqam allaqachon ro'yxatdan o'tgan. Kiring yoki parolni tiklang.")]}
    )


def invalid_code_error() -> serializers.ValidationError:
    return serializers.ValidationError(
        {"code": [_("Kod noto'g'ri yoki muddati o'tgan. Yangi kod so'rang.")]}
    )


class CsrfProtectedView(APIView):
    """Kirish, ro'yxatdan o'tish va tiklash: foydalanuvchi hali kirmagan bo'lsa ham CSRF
    tekshiriladi (DRF faqat kirgan foydalanuvchida tekshiradi)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        SessionAuthentication().enforce_csrf(request)


def me_data(request: Request, user: User) -> dict[str, Any]:
    return dict(MeSerializer(user, context={"request": request}).data)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """`csrftoken` cookie'sini o'rnatadi; frontend uni `X-CSRFToken` header'ida yuboradi."""

    permission_classes = [AllowAny]

    @extend_schema(responses={204: None}, tags=["auth"])
    def get(self, request: Request) -> Response:
        return Response(status=status.HTTP_204_NO_CONTENT)


class OtpView(CsrfProtectedView):
    throttle_scope = "otp"

    @extend_schema(request=OtpRequestSerializer, responses={200: OtpSentSerializer}, tags=["auth"])
    def post(self, request: Request) -> Response:
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone: str = serializer.validated_data["phone"]
        purpose: str = serializer.validated_data["purpose"]

        registered = User.objects.filter(phone=phone).exists()
        if purpose == OneTimeCode.Purpose.REGISTER and registered:
            raise phone_taken_error()

        # Bog'lash kodi faqat ijtimoiy kirish kutayotgan sessiyada so'raladi.
        pending = services.read_pending_social(request.session)
        if purpose == OneTimeCode.Purpose.LINK and pending is None:
            raise serializers.ValidationError(
                {"purpose": [_("Avval Google yoki Telegram orqali kiring.")]}
            )

        # Noma'lum raqamga ham bir xil javob: akkaunt borligi oshkor bo'lmaydi.
        active = User.objects.filter(phone=phone, is_active=True).exists()
        if purpose == OneTimeCode.Purpose.REGISTER or active:
            try:
                code = otp.issue_code(phone, purpose, get_client_ip(request))
            except otp.OtpCooldownError as exc:
                raise OtpCooldown(wait=exc.seconds) from exc
            except otp.OtpDailyLimitError as exc:
                raise OtpDailyLimit from exc
            services.send_code_sms(phone, code)

        return Response({"resend_in": otp.RESEND_SECONDS})


class RegisterView(CsrfProtectedView):
    throttle_scope = "auth_verify"

    @extend_schema(request=RegisterSerializer, responses={201: MeSerializer}, tags=["auth"])
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects.filter(phone=data["phone"]).exists():
            raise phone_taken_error()
        try:
            otp.consume_code(data["phone"], OneTimeCode.Purpose.REGISTER, data["code"])
        except otp.InvalidCodeError as exc:
            raise invalid_code_error() from exc

        user = services.create_student(
            phone=data["phone"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
            locale=(translation.get_language() or "uz")[:2],
            marketing_consent=data["marketing_consent"],
            referred_by=services.referrer(request.COOKIES.get(services.REFERRAL_COOKIE)),
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        response = Response(me_data(request, user), status=status.HTTP_201_CREATED)
        response.delete_cookie(services.REFERRAL_COOKIE)
        return response


class LoginView(CsrfProtectedView):
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: MeSerializer}, tags=["auth"])
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone: str = serializer.validated_data["phone"]

        if services.is_locked(phone):
            raise LoginLocked
        user = authenticate(request, phone=phone, password=serializer.validated_data["password"])
        if user is None:
            services.register_failure(phone)
            raise serializers.ValidationError(
                {"non_field_errors": [_("Telefon raqami yoki parol noto'g'ri.")]}
            )

        services.clear_failures(phone)
        login(request, user)
        return Response(me_data(request, user))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None}, tags=["auth"])
    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetView(CsrfProtectedView):
    throttle_scope = "auth_verify"

    @extend_schema(request=PasswordResetSerializer, responses={200: MeSerializer}, tags=["auth"])
    def post(self, request: Request) -> Response:
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.filter(phone=data["phone"], is_active=True).first()
        if user is None:
            raise invalid_code_error()
        # Yangi parol qoidalarga mos kelmasa, kod sarflanmaydi.
        try:
            check_password(data["password"], user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail}) from exc
        try:
            otp.consume_code(data["phone"], OneTimeCode.Purpose.RESET, data["code"])
        except otp.InvalidCodeError as exc:
            raise invalid_code_error() from exc

        # Parol o'zgargach, boshqa qurilmalardagi sessiyalar avtomatik yaroqsiz bo'ladi.
        user.set_password(data["password"])
        user.save(update_fields=["password"])
        services.clear_failures(user.phone)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(me_data(request, user))


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MeSerializer}, tags=["profile"])
    def get(self, request: Request) -> Response:
        return Response(me_data(request, request.user))  # type: ignore[arg-type]

    @extend_schema(request=MeSerializer, responses={200: MeSerializer}, tags=["profile"])
    def patch(self, request: Request) -> Response:
        serializer = MeSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(me_data(request, user))


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer, responses={204: None}, tags=["profile"])
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user: User = request.user  # type: ignore[assignment]
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        # Joriy sessiya qoladi, boshqa qurilmalardagilari chiqadi.
        update_session_auth_hash(request, user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Google va Telegram ---


class SocialProvidersView(APIView):
    """Qaysi ijtimoiy tugmalar yoqilgan: sozlanmagani saytda ko'rinmaydi."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: SocialProvidersSerializer}, tags=["auth"])
    def get(self, request: Request) -> Response:
        return Response(
            {
                "google_client_id": settings.GOOGLE_CLIENT_ID if google_enabled() else "",
                "telegram_bot": settings.TELEGRAM_BOT_USERNAME if telegram_enabled() else "",
            }
        )


class SocialLoginBase(CsrfProtectedView):
    """Provayder tokenini tekshiradi; akkaunt tanish bo'lsa kiritadi, aks holda telefon so'raydi."""

    throttle_scope = "login"

    def authenticate_profile(self, request: Request) -> SocialProfile:
        raise NotImplementedError

    def post(self, request: Request) -> Response:
        try:
            profile = self.authenticate_profile(request)
        except SocialAuthError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc

        user = services.find_social_user(profile)
        if user is not None:
            services.forget_pending_social(request.session)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return Response({"status": "ok", "user": me_data(request, user)})

        # Akkaunt hali yo'q: telefon so'ralgunga qadar yaratilmaydi.
        services.remember_pending_social(request.session, profile)
        return Response({"status": "phone_required", "first_name": profile.first_name})


class GoogleLoginView(SocialLoginBase):
    @extend_schema(
        request=GoogleLoginSerializer, responses={200: SocialResultSerializer}, tags=["auth"]
    )
    def post(self, request: Request) -> Response:
        return super().post(request)

    def authenticate_profile(self, request: Request) -> SocialProfile:
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return verify_google(serializer.validated_data["credential"])


class TelegramLoginView(SocialLoginBase):
    @extend_schema(
        request=TelegramLoginSerializer, responses={200: SocialResultSerializer}, tags=["auth"]
    )
    def post(self, request: Request) -> Response:
        return super().post(request)

    def authenticate_profile(self, request: Request) -> SocialProfile:
        serializer = TelegramLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Imzo Telegram yuborgan barcha maydonlar bo'yicha hisoblanadi.
        payload = {key: value for key, value in serializer.validated_data.items() if value != ""}
        return verify_telegram(payload)


class SocialPhoneView(CsrfProtectedView):
    """Ijtimoiy kirishdan keyingi telefon qadami: yangi akkaunt yoki mavjudiga bog'lash."""

    throttle_scope = "auth_verify"

    @extend_schema(
        request=SocialPhoneSerializer, responses={200: SocialResultSerializer}, tags=["auth"]
    )
    def post(self, request: Request) -> Response:
        profile = services.read_pending_social(request.session)
        if profile is None:
            raise serializers.ValidationError(
                {"non_field_errors": [_("Vaqt tugadi. Google yoki Telegram orqali qayta kiring.")]}
            )

        serializer = SocialPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone: str = serializer.validated_data["phone"]
        code: str | None = serializer.validated_data.get("code")

        existing = User.objects.filter(phone=phone).first()
        if existing is None:
            user = services.create_social_user(
                profile,
                phone,
                (translation.get_language() or "uz")[:2],
                marketing_consent=serializer.validated_data["marketing_consent"],
                referred_by=services.referrer(request.COOKIES.get(services.REFERRAL_COOKIE)),
            )
        else:
            if not existing.is_active:
                raise serializers.ValidationError(
                    {"phone": [_("Bu akkaunt bloklangan. Qo'llab-quvvatlash bilan bog'laning.")]}
                )
            # Raqam band: egalik SMS kod bilan isbotlanadi,
            # aks holda begona akkauntni egallab olish mumkin bo'lardi.
            if not code:
                return Response({"status": "code_required"})
            try:
                otp.consume_code(phone, OneTimeCode.Purpose.LINK, code)
            except otp.InvalidCodeError as exc:
                raise invalid_code_error() from exc
            services.link_social(existing, profile)
            user = existing

        services.forget_pending_social(request.session)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"status": "ok", "user": me_data(request, user)})
