"""Buyurtmalar va Click callback'lari."""

import logging
from typing import Any, cast

from django.db.models import Prefetch, QuerySet
from django.utils import translation
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.catalog.models import Course
from apps.core.request import get_client_ip
from apps.notifications.alerts import alert
from apps.rewards import referral
from apps.users.models import User

from . import click, pricing
from .models import Order, PaymentLog, PaymentTransaction
from .serializers import (
    ClickCallbackSerializer,
    ClickResultSerializer,
    OrderCreatedSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)

logger = logging.getLogger(__name__)


def my_orders(user: Any) -> QuerySet[Order]:
    return (
        Order.objects.filter(user=user)
        .select_related("course")
        .prefetch_related(Prefetch("transactions", queryset=PaymentTransaction.objects.all()))
    )


class OrderCreateView(APIView):
    """Buyurtma yaratadi va Click sahifasiga havola qaytaradi."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "orders"

    @extend_schema(
        tags=["payments"], request=OrderCreateSerializer, responses=OrderCreatedSerializer
    )
    def post(self, request: Request) -> Response:
        form = OrderCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data

        # `IsAuthenticated` ortida: foydalanuvchi albatta bor.
        user = cast(User, request.user)
        course: Course = get_object_or_404(Course.objects.all(), slug=data["course"])
        pricing.check_can_buy(user, course, data["study_format"])
        months = data["months"] if data["study_format"] == Order.Format.OFFLINE else 1
        full = pricing.amount_for(course, data["study_format"], months)
        discount = referral.discount_for(user)

        order = Order.objects.create(
            user=user,
            course=course,
            study_format=data["study_format"],
            months=months,
            amount=discount.apply(full) if discount else full,
            full_amount=full,
            discount_percent=discount.percent if discount else 0,
            discount_reason=discount.reason if discount else "",
        )
        referral.attach(order, discount)
        return Response(
            {
                "order": OrderSerializer(order).data,
                # Til Accept-Language'dan (frontend har so'rovda yuboradi).
                "pay_url": click.pay_url(order, translation.get_language() or ""),
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(tags=["payments"], responses=OrderSerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(OrderSerializer(my_orders(request.user), many=True).data)


@extend_schema(tags=["payments"], responses=OrderSerializer)
class OrderDetailView(APIView):
    """Natija sahifasi holatni shu orqali kuzatadi: Click'dan qaytish isbot emas."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        order = get_object_or_404(my_orders(request.user), pk=pk)
        return Response(OrderSerializer(order).data)


@method_decorator(csrf_exempt, name="dispatch")
class ClickCallbackView(APIView):
    """Click serveridan keladigan so'rov: sessiya ham, CSRF ham yo'q — himoya imzoda."""

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    throttle_classes: list[type] = []
    action_name = ""

    def handle(self, callback: click.Callback) -> dict[str, Any]:
        raise NotImplementedError

    def post(self, request: Request) -> Response:
        payload = dict(request.data)
        callback = click.Callback.parse(payload)
        try:
            result = self.handle(callback)
        except click.ClickError as exc:
            result = {
                "click_trans_id": callback.click_trans_id,
                "merchant_trans_id": callback.merchant_trans_id,
                "error": exc.code,
                "error_note": str(exc),
            }
            # Imzo yoki summa mos kelmasa — kalit noto'g'ri sozlangan yoki soxta so'rov.
            if exc.code in (click.SIGN_FAILED, click.BAD_AMOUNT):
                alert(
                    f"click:{self.action_name}:{exc.code}",
                    f"Click {self.action_name}: {exc} (buyurtma {callback.merchant_trans_id})",
                )
        except Exception:
            logger.exception("Click callback xatosi: %s", self.action_name)
            alert(
                f"click:{self.action_name}:internal",
                f"Click {self.action_name} ichki xato (buyurtma {callback.merchant_trans_id}). "
                "Tafsilot Sentry va to'lov loglarida.",
            )
            result = {
                "click_trans_id": callback.click_trans_id,
                "merchant_trans_id": callback.merchant_trans_id,
                "error": click.ACTION_NOT_FOUND,
                "error_note": "Internal error",
            }
        self._log(payload, result, callback, request)
        # Click har doim 200 kutadi: xato kod javob ichida beriladi.
        return Response(result)

    def _log(
        self,
        payload: dict[str, Any],
        result: dict[str, Any],
        callback: click.Callback,
        request: Request,
    ) -> None:
        """Barcha so'rov va javoblar saqlanadi (TZ talabi). Imzo saqlanmaydi."""
        safe = {key: value for key, value in payload.items() if key != "sign_string"}
        raw_id = callback.merchant_trans_id
        order_id = int(raw_id) if raw_id.isdigit() else None
        # Buyurtma topilmasa ham log yoziladi: noto'g'ri so'rovlar ham ko'rinishi kerak.
        if order_id is not None and not Order.objects.filter(pk=order_id).exists():
            order_id = None
        try:
            PaymentLog.objects.create(
                action=self.action_name,
                order_id=order_id,
                request=safe,
                response=result,
                ip=get_client_ip(request),
            )
        except Exception:
            logger.exception("To'lov logi yozilmadi")


@extend_schema(tags=["payments"], request=ClickCallbackSerializer, responses=ClickResultSerializer)
class ClickPrepareView(ClickCallbackView):
    action_name = "prepare"

    def handle(self, callback: click.Callback) -> dict[str, Any]:
        if callback.action != click.ACTION_PREPARE:
            raise click.ClickError(click.ACTION_NOT_FOUND)
        return click.prepare(callback)


@extend_schema(tags=["payments"], request=ClickCallbackSerializer, responses=ClickResultSerializer)
class ClickCompleteView(ClickCallbackView):
    action_name = "complete"

    def handle(self, callback: click.Callback) -> dict[str, Any]:
        if callback.action != click.ACTION_COMPLETE:
            raise click.ClickError(click.ACTION_NOT_FOUND)
        return click.complete(callback)
