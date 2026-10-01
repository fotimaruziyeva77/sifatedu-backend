"""Admin'da video yuklash maydoni.

Fayl brauzerdan to'g'ridan-to'g'ri storage'ga ketadi (presigned multipart), shuning uchun
oddiy `FileInput` emas, o'z widget'i kerak. Maydonning qiymati — `VideoAsset` id'si.
"""

from collections.abc import Mapping
from typing import Any

from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import VideoAsset


class VideoUploadWidget(forms.Widget):
    template_name = "videos/upload_widget.html"

    class Media:
        js = ("videos/upload.js",)
        css = {"all": ("videos/upload.css",)}

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        video = VideoAsset.objects.filter(pk=value).first() if value else None
        context["widget"].update(
            {
                "video": video,
                "start_url": reverse("video-upload-start"),
                "max_mb": settings.MAX_VIDEO_SIZE_MB,
                "labels": {
                    "choose": _("Video faylni tanlang"),
                    "replace": _("Boshqa video yuklash"),
                    "uploading": _("Yuklanmoqda"),
                    "processing": _("Qayta ishlanmoqda — bu bir necha daqiqa oladi"),
                    "ready": _("Video tayyor"),
                    "failed": _("Xato"),
                    "cancel": _("Bekor qilish"),
                },
            }
        )
        return context

    def value_from_datadict(
        self, data: Mapping[str, Any], files: Mapping[str, Any], name: str
    ) -> Any:
        value = data.get(name)
        return value or None
