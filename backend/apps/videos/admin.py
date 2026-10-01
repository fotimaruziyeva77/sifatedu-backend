import logging
from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.catalog.scope import scope_videos

from . import s3
from .models import VideoAsset
from .tasks import process_video

logger = logging.getLogger(__name__)


@admin.register(VideoAsset)
class VideoAssetAdmin(ModelAdmin):
    """Videolar ro'yxati. Yuklash dars sahifasidan bo'ladi, bu yerda holat kuzatiladi."""

    list_display = ("__str__", "show_status", "show_length", "show_size", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "original_name", "uid")
    date_hierarchy = "created_at"
    actions = ("reprocess",)
    readonly_fields = (
        "uid",
        "status",
        "original_name",
        "source_key",
        "source_size",
        "duration_sec",
        "width",
        "height",
        "variants",
        "thumbnail",
        "error",
        "uploaded_by",
        "created_at",
        "updated_at",
    )
    fieldsets = [
        (None, {"fields": ["title", "status", "error"]}),
        (
            _("Fayl"),
            {"fields": ["original_name", "source_key", "source_size", "uid", "uploaded_by"]},
        ),
        (
            _("Natija"),
            {"fields": ["duration_sec", ("width", "height"), "variants", "thumbnail"]},
        ),
        (_("Vaqt"), {"fields": [("created_at", "updated_at")]}),
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[VideoAsset]:
        # O'qituvchi — faqat o'zi yuklagan va o'z kurslaridagi videolar.
        return scope_videos(
            super().get_queryset(request).select_related("uploaded_by"), request.user
        )

    @display(
        description=_("Holat"),
        label={
            VideoAsset.Status.UPLOADING: "info",
            VideoAsset.Status.PROCESSING: "warning",
            VideoAsset.Status.READY: "success",
            VideoAsset.Status.FAILED: "danger",
        },
    )
    def show_status(self, obj: VideoAsset) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description=_("Davomiyligi"), ordering="duration_sec")
    def show_length(self, obj: VideoAsset) -> str:
        if not obj.duration_sec:
            return "—"
        minutes, seconds = divmod(obj.duration_sec, 60)
        return f"{minutes}:{seconds:02d}"

    @display(description=_("Hajmi"), ordering="source_size")
    def show_size(self, obj: VideoAsset) -> str:
        if not obj.source_size:
            return "—"
        return f"{obj.source_size / 1024 / 1024:.1f} MB"

    @admin.action(description=_("Qayta ishlash (ffmpeg)"))
    def reprocess(self, request: HttpRequest, queryset: QuerySet[VideoAsset]) -> None:
        ready = queryset.exclude(status=VideoAsset.Status.UPLOADING)
        count = 0
        for video in ready:
            VideoAsset.objects.filter(pk=video.pk).update(
                status=VideoAsset.Status.PROCESSING, error=""
            )
            process_video.delay(video.pk)
            count += 1
        self.message_user(
            request,
            ngettext("%d video navbatga qo'yildi.", "%d video navbatga qo'yildi.", count) % count,
            messages.SUCCESS if count else messages.WARNING,
        )

    def delete_model(self, request: HttpRequest, obj: VideoAsset) -> None:
        # Bazadan o'chirilganda storage'da yetim fayllar qolmasligi kerak.
        self._purge(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[VideoAsset]) -> None:
        for obj in queryset:
            self._purge(obj)
        super().delete_queryset(request, queryset)

    def _purge(self, obj: VideoAsset) -> None:
        try:
            s3.delete_prefix(f"{obj.prefix}/")
        except Exception:
            # Storage javob bermasa ham yozuvni o'chirishga to'sqinlik qilmaydi.
            logger.exception("Video fayllari o'chirilmadi: %s", obj.uid)

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        # Video faqat dars sahifasidagi yuklash maydoni orqali paydo bo'ladi.
        return False
