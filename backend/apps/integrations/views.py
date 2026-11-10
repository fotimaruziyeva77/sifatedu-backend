"""Markaz sozlamalari (faqat ADMIN roli) va egasining birinchi kirishi."""

from typing import Any

from django.conf import settings
from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Course
from apps.content.models import LegalPage, SiteSettings
from apps.learning.models import StudyGroup
from apps.notifications import sms
from apps.tenancy.access import current_center, has_feature, require_feature
from apps.tenancy.models import Center
from apps.tenancy.sections import Feature
from apps.tenancy.signup import take_welcome
from apps.tenancy.sites import center_name, site_url
from apps.users.models import User
from apps.users.roles import Role, has_role

from . import conf, services
from .models import Integrations
from .serializers import (
    BrandSerializer,
    CenterSetupSerializer,
    ClickSerializer,
    EskizSerializer,
    TelegramConnectSerializer,
    TelegramOptionsSerializer,
)

CENTER_PAGE = "dashboard/center"
LEGAL_REQUIRED = (LegalPage.Slug.OFFER, LegalPage.Slug.PRIVACY)


class IsCenterAdmin(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        return has_role(request.user, Role.ADMIN)


def _setup_data() -> dict[str, Any]:
    site = SiteSettings.load()
    bot = conf.telegram()
    click = conf.click()
    eskiz = conf.eskiz()
    base = site_url()
    return {
        "name": center_name(),
        "address": base.split("://", 1)[-1],
        "color": site.brand_color,
        "logo": site.logo.url if site.logo else "",
        "logo_dark": site.logo_dark.url if site.logo_dark else "",
        "steps": {
            "brand": bool(site.logo or site.brand_color),
            "course": Course.objects.exists(),
            "group": StudyGroup.objects.exists(),
            "legal": LegalPage.objects.filter(slug__in=LEGAL_REQUIRED).count()
            == len(LEGAL_REQUIRED),
        },
        "admin": {
            "course_add": reverse("admin:catalog_course_add"),
            "group_add": reverse("admin:learning_studygroup_add"),
            "site": reverse("admin:content_sitesettings_change", args=[site.pk]),
            "legal": reverse("admin:content_legalpage_changelist"),
        },
        "telegram": {
            "available": has_feature(Feature.BOT),
            "connected": bool(bot.token),
            "username": bot.username,
            "login": bot.login,
            "leads_chat": bot.leads_chat,
            "reports_chat": bot.reports_chat,
        },
        "click": {
            "available": has_feature(Feature.CLICK),
            "connected": click.ready,
            "service_id": click.service_id,
            "merchant_id": click.merchant_id,
            "merchant_user_id": click.merchant_user_id,
            "tin": click.tin,
            "prepare_url": f"{base}{reverse('click-prepare')}",
            "complete_url": f"{base}{reverse('click-complete')}",
        },
        "eskiz": {
            "available": has_feature(Feature.BOT),
            "connected": eskiz.ready,
            "email": eskiz.email,
            "sender": eskiz.sender,
        },
    }


def _setup_response() -> Response:
    return Response(_setup_data())


class SetupView(APIView):
    permission_classes = [IsCenterAdmin]

    @extend_schema(responses=CenterSetupSerializer, tags=["center"])
    def get(self, request: Request) -> Response:
        return _setup_response()


class BrandView(APIView):
    permission_classes = [IsCenterAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": BrandSerializer, "application/json": BrandSerializer},
        responses=CenterSetupSerializer,
        tags=["center"],
    )
    def patch(self, request: Request) -> Response:
        serializer = BrandSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        site = SiteSettings.load()
        changed = ["updated_at"]
        if "color" in data:
            site.brand_color = data["color"]
            changed.append("brand_color")
        for field in ("logo", "logo_dark"):
            if field in data:
                # `None` — logoni olib tashlash.
                setattr(site, field, data[field] or "")
                changed.append(field)
        # Keshni tozalovchi signal `save` orqali ishlaydi.
        site.save(update_fields=changed)
        if "name" in data:
            center = current_center()
            if center is not None:
                Center.objects.filter(pk=center.pk).update(name=data["name"])
                # Shu so'rovning javobida ham yangi nom chiqsin.
                center.name = data["name"]
        return _setup_response()


class TelegramView(APIView):
    permission_classes = [IsCenterAdmin]

    @extend_schema(
        request=TelegramConnectSerializer, responses=CenterSetupSerializer, tags=["center"]
    )
    def put(self, request: Request) -> Response:
        require_feature(Feature.BOT)
        serializer = TelegramConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.connect_telegram(serializer.validated_data["token"])
        return _setup_response()

    @extend_schema(
        request=TelegramOptionsSerializer, responses=CenterSetupSerializer, tags=["center"]
    )
    def patch(self, request: Request) -> Response:
        require_feature(Feature.BOT)
        serializer = TelegramOptionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        fields = {
            "leads_chat": "telegram_leads_chat_id",
            "reports_chat": "telegram_reports_chat_id",
            "login": "telegram_login",
        }
        row = Integrations.load()
        for key, field in fields.items():
            if key in data:
                setattr(row, field, data[key])
        row.save(update_fields=[*fields.values(), "updated_at"])
        return _setup_response()

    @extend_schema(request=None, responses={204: None}, tags=["center"])
    def delete(self, request: Request) -> Response:
        services.disconnect_telegram()
        return Response(status=204)


class ClickView(APIView):
    permission_classes = [IsCenterAdmin]

    @extend_schema(request=ClickSerializer, responses=CenterSetupSerializer, tags=["center"])
    def put(self, request: Request) -> Response:
        require_feature(Feature.CLICK)
        row = Integrations.load()
        serializer = ClickSerializer(
            data=request.data, context={"has_secret": bool(row.click_secret_key)}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        row.click_service_id = data["service_id"]
        row.click_merchant_id = data["merchant_id"]
        row.click_merchant_user_id = data.get("merchant_user_id", "")
        row.click_tin = data.get("tin", "")
        if data.get("secret_key"):
            row.click_secret_key = data["secret_key"]
        row.save()
        return _setup_response()

    @extend_schema(request=None, responses={204: None}, tags=["center"])
    def delete(self, request: Request) -> Response:
        Integrations.objects.filter(pk=1).update(
            click_service_id="",
            click_merchant_id="",
            click_merchant_user_id="",
            click_secret_key="",
            click_tin="",
        )
        return Response(status=204)


class EskizView(APIView):
    permission_classes = [IsCenterAdmin]

    @extend_schema(request=EskizSerializer, responses=CenterSetupSerializer, tags=["center"])
    def put(self, request: Request) -> Response:
        require_feature(Feature.BOT)
        serializer = EskizSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.connect_eskiz(data["email"], data["password"], data.get("sender", ""))
        return _setup_response()

    @extend_schema(request=None, responses={204: None}, tags=["center"])
    def delete(self, request: Request) -> Response:
        Integrations.objects.filter(pk=1).update(eskiz_email="", eskiz_password="", eskiz_from="")
        sms.forget_token()
        return Response(status=204)


class WelcomeView(View):
    """Markaz tayyor bo'lgach egasini bir martalik havola bilan kabinetga kiritadi."""

    feature = None

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        user_id = take_welcome(token)
        user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None
        locale = (user.locale if user else "") or settings.LANGUAGE_CODE
        if user is None:
            target = f"/{locale}/auth/login"
        else:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            target = f"/{locale}/{CENTER_PAGE}"
        response = HttpResponseRedirect(target)
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response
