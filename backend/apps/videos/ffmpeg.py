"""ffmpeg/ffprobe chaqiruvlari. Buyruqlar alohida funksiyalarda: testlarda tekshiriladi."""

import json
import logging
import subprocess  # buyruqlar ro'yxat sifatida beriladi, shell ishlatilmaydi
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# ffmpeg katta fayllarda uzoq ishlaydi; cheksiz kutib qolmaslik uchun chegara qo'yiladi.
PROBE_TIMEOUT = 60
ENCODE_TIMEOUT = 60 * 60 * 6
SEGMENT_SECONDS = 6
# Segment chegaralari aniq bo'lishi uchun kalit kadr oralig'i FPS'ga bog'lanmaydi.
KEYFRAME_INTERVAL = 48


@dataclass(frozen=True)
class Rendition:
    height: int
    video_kbps: int
    audio_kbps: int

    @property
    def name(self) -> str:
        return f"{self.height}p"

    @property
    def bandwidth(self) -> int:
        # Master playlist'dagi BANDWIDTH cho'qqi tezlikni ko'rsatadi.
        return int((self.video_kbps + self.audio_kbps) * 1100)


# 480p 1.5 Mbit/s dan past: sekin internetda ham uzilmasligi kerak.
RENDITIONS = (
    Rendition(360, 800, 96),
    Rendition(480, 1200, 128),
    Rendition(720, 2500, 128),
    Rendition(1080, 4500, 192),
)


@dataclass(frozen=True)
class SourceInfo:
    duration_sec: int
    width: int
    height: int


class FfmpegError(RuntimeError):
    pass


def _run(command: list[str], timeout: int) -> str:
    logger.info("ffmpeg: %s", " ".join(command[:6]))
    try:
        result = subprocess.run(  # noqa: S603 - buyruq ro'yxat, foydalanuvchi matni argument emas
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise FfmpegError("Video juda uzoq ishlov berildi (timeout).") from exc
    if result.returncode != 0:
        # stderr uzun bo'ladi: admin'da foydali bo'lgan oxirgi qismi qoldiriladi.
        raise FfmpegError(result.stderr.strip()[-2000:] or "ffmpeg xatosi")
    return result.stdout


def probe(source: Path) -> SourceInfo:
    output = _run(
        [
            settings.FFPROBE_BIN,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(source),
        ],
        PROBE_TIMEOUT,
    )
    data = json.loads(output or "{}")
    streams = data.get("streams") or []
    if not streams:
        raise FfmpegError("Faylda video oqimi topilmadi.")
    stream = streams[0]
    duration = float(data.get("format", {}).get("duration") or 0)
    return SourceInfo(
        duration_sec=max(1, round(duration)),
        width=int(stream.get("width") or 0),
        height=int(stream.get("height") or 0),
    )


def renditions_for(height: int) -> list[Rendition]:
    """Manba sifatidan yuqorisini yasash ma'nosiz: faqat mos keladiganlari qoladi."""
    fitting = [item for item in RENDITIONS if item.height <= height]
    return fitting or [RENDITIONS[0]]


def thumbnail_command(source: Path, target: Path, at_sec: int) -> list[str]:
    return [
        settings.FFMPEG_BIN,
        "-y",
        "-ss",
        str(at_sec),
        "-i",
        str(source),
        "-frames:v",
        "1",
        # Kartochkada ham, pleyerda ham yetarli: balandligi 720, kengligi juft.
        "-vf",
        r"scale=-2:min(720\,ih)",
        "-q:v",
        "3",
        str(target),
    ]


def hls_command(source: Path, out_dir: Path, rendition: Rendition, key_info: Path) -> list[str]:
    """Bitta sifat uchun shifrlangan HLS. Har sifat alohida chaqiriladi: xotira kam ketadi."""
    return [
        settings.FFMPEG_BIN,
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        # Ovozsiz video ham bo'lishi mumkin: "?" bilan majburiy emas.
        "-map",
        "0:a:0?",
        "-vf",
        f"scale=-2:{rendition.height}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-profile:v",
        "main",
        "-crf",
        "23",
        "-maxrate",
        f"{rendition.video_kbps}k",
        "-bufsize",
        f"{rendition.video_kbps * 2}k",
        "-g",
        str(KEYFRAME_INTERVAL),
        "-keyint_min",
        str(KEYFRAME_INTERVAL),
        "-sc_threshold",
        "0",
        "-c:a",
        "aac",
        "-b:a",
        f"{rendition.audio_kbps}k",
        "-ac",
        "2",
        "-f",
        "hls",
        "-hls_time",
        str(SEGMENT_SECONDS),
        "-hls_playlist_type",
        "vod",
        "-hls_key_info_file",
        str(key_info),
        "-hls_segment_filename",
        str(out_dir / "seg_%04d.ts"),
        str(out_dir / "index.m3u8"),
    ]


def run_thumbnail(source: Path, target: Path, at_sec: int) -> None:
    _run(thumbnail_command(source, target, at_sec), PROBE_TIMEOUT)


def run_hls(source: Path, out_dir: Path, rendition: Rendition, key_info: Path) -> None:
    _run(hls_command(source, out_dir, rendition, key_info), ENCODE_TIMEOUT)
