from typing import Any

from rest_framework import serializers

from .models import Product, Purchase


class ProductSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    image = serializers.CharField(help_text="Rasm manzili (bo'lmasa — bo'sh).")
    price = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=Product.Kind.choices)
    stock = serializers.IntegerField(allow_null=True, help_text="Qolgan soni; null — cheksiz.")
    affordable = serializers.BooleanField(help_text="Coin yetadimi.")


class ShopSerializer(serializers.Serializer[dict[str, Any]]):
    coins = serializers.IntegerField()
    products = ProductSerializer(many=True)


class PurchaseSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    image = serializers.CharField()
    price = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Purchase.Status.choices)
    note = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class BoughtSerializer(serializers.Serializer[dict[str, Any]]):
    purchase = PurchaseSerializer()
    coins = serializers.IntegerField(help_text="Qolgan coin.")
