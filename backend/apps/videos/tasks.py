"""Video qayta ishlash: ffmpeg bilan shifrlangan HLS, suratcha va davomiylik.

`video` navbatida, bitta jarayonda ishlaydi (ffmpeg og'ir). Vazifa faqat bitta VideoAsset
bilan ishlaydi, shuning uchun xato bo'lsa faqat o'sha video `FAILED` bo'ladi.
"""

import logging
import shutil
import tempfile
from pathlib import Path

from celery import shared_task
from django.core.files.base import ContentFile
from django.db import transaction

from apps.notifications.alerts import alert

from . import ffmpeg, s3
from .models import VideoAsset

logger = logging.getLogger(__name__)

# Suratcha videoning boshidagi qora kadrga tushmasligi uchun sal ichkaridan olinadi.
THUMB_AT_RATIO = 0.1


@shared_task(bind=True, max_retries=0, acks_late=True)
def process_video(self: object, video_id: int) -> str:
    video = VideoAsset.objects.filter(pk=video_id).first()
    if video is None:
        return "yo'q"
    try:
        _process(video)
    except Exception as exc:  # Xato admin'da ko'rinishi kerak.
        logger.exception("Video qayta ishlanmadi: %s", video.uid)
        VideoAsset.objects.filter(pk=video.pk).update(
            status=VideoAsset.Status.FAILED, error=str(exc)[:2000]
        )
        alert(f"video:failed:{video.pk}", f"Video qayta ishlanmadi: «{video}» (id {video.pk})")
        return "xato"
    return "tayyor"


def _process(video: VideoAsset) -> None:
    workdir = Path(tempfile.mkdtemp(prefix="sifat-video-"))
    try:
        source = workdir / "source"
        s3.download(video.source_key, str(source))
        info = ffmpeg.probe(source)

        _thumbnail(video, source, workdir, info)
        variants = _renditions(video, source, workdir, info)

        video.duration_sec = info.duration_sec
        video.width = info.width
        video.height = info.height
        video.variants = variants
        video.status = VideoAsset.Status.READY
        video.error = ""
        video.save(
            update_fields=[
                "duration_sec",
                "width",
                "height",
                "variants",
                "status",
                "error",
                "updated_at",
            ]
        )
        transaction.on_commit(lambda: _sync_lessons(video.pk, info.duration_sec))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _thumbnail(video: VideoAsset, source: Path, workdir: Path, info: ffmpeg.SourceInfo) -> None:
    target = workdir / "thumb.jpg"
    at = max(1, int(info.duration_sec * THUMB_AT_RATIO))
    ffmpeg.run_thumbnail(source, target, at)
    with target.open("rb") as handle:
        video.thumbnail.save("thumb.jpg", ContentFile(handle.read()), save=True)


def _renditions(
    video: VideoAsset, source: Path, workdir: Path, info: ffmpeg.SourceInfo
) -> list[dict[str, object]]:
    key_file = workdir / "enc.key"
    key_file.write_bytes(video.ensure_key())
    # ffmpeg shu URI'ni playlist'ga yozadi; so'rov paytida u backend havolasiga almashtiriladi.
    key_info = workdir / "enc.keyinfo"
    key_info.write_text(f"sifat://key\n{key_file}\n", encoding="utf-8")

    variants: list[dict[str, object]] = []
    for rendition in ffmpeg.renditions_for(info.height):
        out_dir = workdir / rendition.name
        out_dir.mkdir()
        ffmpeg.run_hls(source, out_dir, rendition, key_info)
        _upload_dir(video, out_dir, rendition.name)
        variants.append(
            {
                "height": rendition.height,
                "width": _scaled_width(info, rendition.height),
                "bandwidth": rendition.bandwidth,
                "playlist": f"{rendition.name}/index.m3u8",
            }
        )
    return variants


def _scaled_width(info: ffmpeg.SourceInfo, height: int) -> int:
    """ffmpeg kenglikni juft qiladi (`scale=-2`), master playlist ham shuni ko'rsatadi."""
    if not info.height:
        return 0
    return round(info.width * height / info.height / 2) * 2


def _upload_dir(video: VideoAsset, out_dir: Path, name: str) -> None:
    for path in sorted(out_dir.iterdir()):
        content_type = "application/vnd.apple.mpegurl" if path.suffix == ".m3u8" else "video/mp2t"
        s3.put_file(f"{video.hls_prefix}/{name}/{path.name}", str(path), content_type)


def _sync_lessons(video_id: int, duration_sec: int) -> None:
    """Dars davomiyligi video davomiyligidan olinadi (dastur hajmi to'g'ri ko'rinsin)."""
    from apps.catalog.models import Lesson

    minutes = max(1, round(duration_sec / 60))
    for lesson in Lesson.objects.filter(video_id=video_id):
        if lesson.duration_min != minutes:
            lesson.duration_min = minutes
            lesson.save(update_fields=["duration_min", "updated_at"])
