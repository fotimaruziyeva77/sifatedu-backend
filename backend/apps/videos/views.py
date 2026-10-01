"""Admin uchun video yuklash: brauzer faylni to'g'ridan-to'g'ri storage'ga yuboradi.

Backend faqat multipart sessiyani boshqaradi va har qism uchun imzolangan URL beradi:
shu sababli 2 GB fayl Django orqali o'tmaydi.
"""

import contextlib
import math
from typing import Any

from botocore.exceptions import ClientError
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import BasePermission, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import s3
from .models import VideoAsset
from .serializers import (
    UploadCompleteSerializer,
    UploadPartResultSerializer,
    UploadPartsSerializer,
    UploadStartedSerializer,
    UploadStartSerializer,
    VideoAssetSerializer,
)
from .tasks import process_video


class CanUploadVideos(BasePermission):
    """Video yuklash huquqi bor xodim (Admin, O'qituvchi). Direktor faqat ko'radi."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user.has_perm("videos.add_videoasset"))


class StaffVideoView(APIView):
    """Faqat xodimlar uchun: video admin panel orqali yuklanadi."""

    permission_classes = [IsAdminUser, CanUploadVideos]
    throttle_classes = []

    def get_asset(self, pk: int) -> VideoAsset:
        return get_object_or_404(VideoAsset.objects.all(), pk=pk)

    def require_uploading(self, video: VideoAsset) -> None:
        if video.status != VideoAsset.Status.UPLOADING or not video.upload_id:
            raise ValidationError({"detail": "Bu video yuklash holatida emas."})


@extend_schema(tags=["videos"], request=UploadStartSerializer, responses=UploadStartedSerializer)
class UploadStartView(StaffVideoView):
    def post(self, request: Request) -> Response:
        form = UploadStartSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        payload = form.validated_data

        video = VideoAsset.objects.create(
            title=payload.get("title") or payload["filename"],
            original_name=payload["filename"][:255],
            source_size=payload["size"],
            uploaded_by_id=request.user.pk,
        )
        try:
            video.upload_id = s3.start_multipart(
                video.source_key, payload.get("content_type") or ""
            )
        except ClientError as exc:
            video.delete()
            raise ValidationError({"detail": f"Storage javob bermadi: {exc}"}) from exc
        video.save(update_fields=["upload_id", "updated_at"])

        part_size = settings.VIDEO_PART_SIZE_MB * 1024 * 1024
        return Response(
            {
                "video": VideoAssetSerializer(video).data,
                "part_size": part_size,
                "part_count": math.ceil(payload["size"] / part_size),
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["videos"],
    request=UploadPartsSerializer,
    responses=UploadPartResultSerializer(many=True),
)
class UploadPartsView(StaffVideoView):
    def post(self, request: Request, pk: int) -> Response:
        video = self.get_asset(pk)
        self.require_uploading(video)
        form = UploadPartsSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        ttl = settings.HLS_SIGNED_URL_TTL_SEC
        return Response(
            [
                {
                    "part_number": number,
                    "url": s3.sign_part(video.source_key, video.upload_id, number, ttl),
                }
                for number in form.validated_data["part_numbers"]
            ]
        )


@extend_schema(tags=["videos"], request=UploadCompleteSerializer, responses=VideoAssetSerializer)
class UploadCompleteView(StaffVideoView):
    def post(self, request: Request, pk: int) -> Response:
        video = self.get_asset(pk)
        self.require_uploading(video)
        form = UploadCompleteSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        parts: list[dict[str, Any]] = form.validated_data["parts"]
        try:
            size = s3.finish_multipart(video.source_key, video.upload_id, parts)
        except ClientError as exc:
            raise ValidationError({"detail": f"Qismlar birlashmadi: {exc}"}) from exc

        video.source_size = size
        video.upload_id = ""
        video.status = VideoAsset.Status.PROCESSING
        video.save(update_fields=["source_size", "upload_id", "status", "updated_at"])
        process_video.delay(video.pk)
        return Response(VideoAssetSerializer(video).data)


@extend_schema(tags=["videos"], request=None, responses={204: None})
class UploadAbortView(StaffVideoView):
    def post(self, request: Request, pk: int) -> Response:
        video = self.get_asset(pk)
        if video.upload_id:
            # Sessiya allaqachon yopilgan bo'lishi mumkin: yozuvni o'chirish muhimroq.
            with contextlib.suppress(ClientError):
                s3.cancel_multipart(video.source_key, video.upload_id)
        if video.status == VideoAsset.Status.UPLOADING:
            video.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["videos"], responses=VideoAssetSerializer)
class VideoStatusView(StaffVideoView):
    """Admin sahifasi qayta ishlash tugaganini shu orqali kuzatadi."""

    def get(self, request: Request, pk: int) -> Response:
        return Response(VideoAssetSerializer(self.get_asset(pk)).data)
