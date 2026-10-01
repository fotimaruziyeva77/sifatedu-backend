from typing import Any

from rest_framework import serializers

from apps.core.serializers import ReadOnlyModelSerializer

from .models import MAX_MONTHS, Order


class OrderCreateSerializer(serializers.Serializer[dict[str, Any]]):
    """Summa yuborilmaydi — uni backend hisoblaydi."""

    course = serializers.SlugField(max_length=60)
    study_format = serializers.ChoiceField(choices=Order.Format.choices)
    months = serializers.IntegerField(min_value=1, max_value=MAX_MONTHS, default=1)


class OrderSerializer(ReadOnlyModelSerializer):
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    receipt_url = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "course_slug",
            "course_title",
            "study_format",
            "months",
            "amount",
            "full_amount",
            "discount_percent",
            "discount_reason",
            "status",
            "provider",
            "paid_at",
            "created_at",
            "receipt_url",
        )

    def get_receipt_url(self, obj: Order) -> str:
        payment = next((item for item in obj.transactions.all() if item.fiscal_receipt_url), None)
        return payment.fiscal_receipt_url if payment else ""


class OrderCreatedSerializer(serializers.Serializer[dict[str, Any]]):
    order = OrderSerializer()
    pay_url = serializers.CharField()


class ClickCallbackSerializer(serializers.Serializer[dict[str, Any]]):
    """Faqat sxema uchun: qiymatlar `apps/payments/click.py` da tekshiriladi."""

    click_trans_id = serializers.CharField()
    service_id = serializers.CharField()
    click_paydoc_id = serializers.CharField(required=False, allow_blank=True)
    merchant_trans_id = serializers.CharField()
    merchant_prepare_id = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.CharField()
    action = serializers.CharField()
    error = serializers.CharField(required=False, allow_blank=True)
    error_note = serializers.CharField(required=False, allow_blank=True)
    sign_time = serializers.CharField()
    sign_string = serializers.CharField()


class ClickResultSerializer(serializers.Serializer[dict[str, Any]]):
    click_trans_id = serializers.CharField()
    merchant_trans_id = serializers.CharField()
    merchant_prepare_id = serializers.IntegerField(required=False)
    merchant_confirm_id = serializers.IntegerField(required=False)
    error = serializers.IntegerField()
    error_note = serializers.CharField()
