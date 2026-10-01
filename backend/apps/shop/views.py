"""Do'kon API: sovg'alar (coin balansi bilan), olish va buyurtmalarim."""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.rewards import services as rewards
from apps.users.models import User

from . import services
from .models import Product, Purchase
from .serializers import BoughtSerializer, PurchaseSerializer, ShopSerializer


def image_url(product: Product) -> str:
    return product.image.url if product.image else ""


def product_payload(product: Product, coins: int) -> dict[str, Any]:
    return {
        "id": product.pk,
        "name": product.name,
        "description": product.description,
        "image": image_url(product),
        "price": product.price,
        "kind": product.kind,
        "stock": product.stock,
        "affordable": coins >= product.price,
    }


def purchase_payload(purchase: Purchase) -> dict[str, Any]:
    return {
        "id": purchase.pk,
        "name": purchase.name,
        "image": image_url(purchase.product),
        "price": purchase.price,
        "status": purchase.status,
        "note": purchase.note,
        "created_at": purchase.created_at,
        "updated_at": purchase.updated_at,
    }


class ShopView(APIView):
    """Sotuvdagi sovg'alar (o'quvchining ko'rinishiga mos) va coin balansi."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ShopSerializer}, tags=["shop"])
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        coins = rewards.wallet_of(user.pk).coins
        products = [product for product in services.catalog(user) if product.in_stock]
        return Response(
            {"coins": coins, "products": [product_payload(item, coins) for item in products]}
        )


class BuyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "orders"

    @extend_schema(request=None, responses={201: BoughtSerializer}, tags=["shop"])
    def post(self, request: Request, pk: int) -> Response:
        user: User = request.user  # type: ignore[assignment]
        try:
            purchase = services.buy(user, pk)
        except services.ShopError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(
            {"purchase": purchase_payload(purchase), "coins": rewards.wallet_of(user.pk).coins},
            status=201,
        )


class MyPurchasesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PurchaseSerializer(many=True)}, tags=["shop"])
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        rows = Purchase.objects.filter(user=user).select_related("product")
        return Response([purchase_payload(item) for item in rows])
