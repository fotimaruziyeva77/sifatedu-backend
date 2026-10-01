from typing import Any

from django.conf import settings
from rest_framework import serializers

from apps.core.serializers import ReadOnlyModelSerializer

from .models import VideoAsset


class UploadStartSerializer(serializers.Serializer[dict[str, Any]]):
    filename = serializers.CharField(max_length=255)
    size = serializers.IntegerField(min_value=1)
    content_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_size(self, value: int) -> int:
        limit = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
        if value > limit:
            raise serializers.ValidationError(
                f"Fayl juda katta. Ruxsat etilgan hajm: {settings.MAX_VIDEO_SIZE_MB} MB."
            )
        return value


class UploadPartsSerializer(serializers.Serializer[dict[str, Any]]):
    # Brauzer URL'larni to'plam-to'plam so'raydi: imzo muddati o'tib ketmasligi uchun.
    part_numbers = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=10_000),
        min_length=1,
        max_length=50,
    )


class UploadPartResultSerializer(serializers.Serializer[dict[str, Any]]):
    part_number = serializers.IntegerField()
    url = serializers.CharField()


class CompletedPartSerializer(serializers.Serializer[dict[str, Any]]):
    part_number = serializers.IntegerField(min_value=1)
    etag = serializers.CharField(max_length=200)


class UploadCompleteSerializer(serializers.Serializer[dict[str, Any]]):
    parts = CompletedPartSerializer(many=True)


class VideoAssetSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = VideoAsset
        fields = (
            "id",
            "uid",
            "title",
            "status",
            "original_name",
            "duration_sec",
            "width",
            "height",
            "thumbnail",
            "error",
        )


class UploadStartedSerializer(serializers.Serializer[dict[str, Any]]):
    video = VideoAssetSerializer()
    part_size = serializers.IntegerField()
    part_count = serializers.IntegerField()
