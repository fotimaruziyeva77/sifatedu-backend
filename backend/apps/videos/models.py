"""Video fayl va uning HLS ko'rinishlari."""

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.core.storage import public_storage

from . import crypto


def thumbnail_path(instance: "VideoAsset", filename: str) -> str:
    return f"video-thumbs/{instance.uid}.jpg"


class VideoAsset(TimeStampedModel):
    """Yuklangan video va undan yasalgan HLS ko'rinishlari.

    Fayllar yopiq bucket'da `videos/<uid>/` ostida turadi: xom fayl `source/`,
    HLS esa `hls/`. Ularga faqat imzolangan qisqa muddatli havola bilan kirish mumkin.
    """

    class Status(models.TextChoices):
        UPLOADING = "UPLOADING", _("Yuklanmoqda")
        PROCESSING = "PROCESSING", _("Qayta ishlanmoqda")
        READY = "READY", _("Tayyor")
        FAILED = "FAILED", _("Xato")

    uid = models.UUIDField(_("identifikator"), default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(_("nomi"), max_length=200, blank=True)
    status = models.CharField(
        _("holat"),
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADING,
        db_index=True,
    )
    original_name = models.CharField(_("fayl nomi"), max_length=255, blank=True)
    source_key = models.CharField(_("xom fayl kaliti"), max_length=255, blank=True)
    source_size = models.BigIntegerField(_("hajmi (bayt)"), default=0)
    upload_id = models.CharField(_("multipart id"), max_length=255, blank=True)

    duration_sec = models.PositiveIntegerField(_("davomiyligi (soniya)"), default=0)
    width = models.PositiveIntegerField(_("kengligi"), default=0)
    height = models.PositiveIntegerField(_("balandligi"), default=0)
    # [{"height": 720, "bandwidth": 2928000, "playlist": "720p/index.m3u8"}]
    variants = models.JSONField(_("sifatlar"), default=list, blank=True)
    thumbnail = models.ImageField(
        _("suratcha"), storage=public_storage, upload_to=thumbnail_path, blank=True
    )
    # AES-128 kaliti Fernet bilan shifrlangan holda (apps/videos/crypto.py).
    sealed_key = models.TextField(_("shifrlash kaliti"), blank=True, editable=False)
    error = models.TextField(_("xato"), blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("yuklagan"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_videos",
    )

    class Meta:
        verbose_name = _("video")
        verbose_name_plural = _("videolar")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title or self.original_name or str(self.uid)

    @property
    def prefix(self) -> str:
        return f"videos/{self.uid}"

    @property
    def hls_prefix(self) -> str:
        return f"{self.prefix}/hls"

    @property
    def is_ready(self) -> bool:
        return self.status == self.Status.READY and bool(self.variants)

    def ensure_key(self) -> bytes:
        """Shifrlash kalitini qaytaradi, birinchi murojaatda yaratadi."""
        if not self.sealed_key:
            self.sealed_key = crypto.seal(crypto.new_key())
            self.save(update_fields=["sealed_key", "updated_at"])
        return crypto.unseal(self.sealed_key)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.source_key:
            self.source_key = f"{self.prefix}/source/{self.uid}"
        super().save(*args, **kwargs)
