from typing import Any

from rest_framework import serializers


class ReadOnlyModelSerializer(serializers.ModelSerializer[Any]):
    """Faqat javob uchun: barcha maydonlar read_only.

    Shunda OpenAPI sxemasida ular majburiy bo'ladi va frontend tiplari aniqroq chiqadi.
    """

    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields
