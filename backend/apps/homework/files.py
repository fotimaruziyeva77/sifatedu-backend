"""Javob fayllarini tekshirish: soni, hajmi, turi. Fayllar hech qachon ochilmaydi va ishga
tushirilmaydi — faqat saqlanadi va yuklab olish uchun beriladi."""

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename
from django.utils.translation import gettext as _
from PIL import Image, UnidentifiedImageError

MAX_FILES = 5
MAX_FILE_MB = 20
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
# Bitta javobdagi barcha fayllar (nginx'da shu yo'l uchun 55 MB).
MAX_TOTAL_MB = 50
MAX_TOTAL_BYTES = MAX_TOTAL_MB * 1024 * 1024

# Brauzerda rasm sifatida ko'rsatiladiganlar. SVG ichida skript bo'lishi mumkin — oddiy fayl.
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | frozenset(
    {
        # hujjatlar
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".txt",
        ".md",
        ".csv",
        # arxivlar (ochilmaydi)
        ".zip",
        ".rar",
        ".7z",
        # kod
        ".html",
        ".css",
        ".scss",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".json",
        ".py",
        ".ipynb",
        ".java",
        ".kt",
        ".c",
        ".cpp",
        ".h",
        ".cs",
        ".php",
        ".go",
        ".sql",
        ".swift",
        # dizayn, Scratch, qisqa videolar
        ".svg",
        ".fig",
        ".psd",
        ".sb3",
        ".mp4",
        ".webm",
    }
)


class FileRejected(ValueError):
    """Foydalanuvchiga ko'rsatiladigan sabab bilan."""


@dataclass(frozen=True)
class CheckedFile:
    upload: UploadedFile
    name: str
    size: int
    content_type: str
    is_image: bool


def clean_name(raw: str) -> str:
    """Faqat fayl nomi (yo'lsiz), xavfsiz belgilar; uzunligi cheklangan."""
    name = get_valid_filename(Path(raw or "fayl").name) or "fayl"
    stem, suffix = Path(name).stem[:120], Path(name).suffix.lower()[:12]
    return f"{stem}{suffix}"


def check(uploads: list[UploadedFile]) -> list[CheckedFile]:
    if len(uploads) > MAX_FILES:
        raise FileRejected(
            _("Ko'pi bilan %(count)s ta fayl yuborish mumkin.") % {"count": MAX_FILES}
        )
    checked = []
    for upload in uploads:
        name = clean_name(upload.name or "")
        suffix = Path(name).suffix
        if suffix not in ALLOWED_EXTENSIONS:
            raise FileRejected(_("«%(name)s»: bu turdagi fayl qabul qilinmaydi.") % {"name": name})
        size = int(upload.size or 0)
        if size > MAX_FILE_BYTES:
            raise FileRejected(
                _("«%(name)s» juda katta: har bir fayl %(mb)s MB gacha.")
                % {"name": name, "mb": MAX_FILE_MB}
            )
        if size == 0:
            raise FileRejected(_("«%(name)s» bo'sh fayl.") % {"name": name})
        is_image = suffix in IMAGE_EXTENSIONS
        if is_image:
            ensure_image(upload, name)
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        checked.append(CheckedFile(upload, name, size, content_type, is_image))
    if sum(item.size for item in checked) > MAX_TOTAL_BYTES:
        raise FileRejected(_("Fayllar jami %(mb)s MB dan oshmasin.") % {"mb": MAX_TOTAL_MB})
    return checked


def ensure_image(upload: UploadedFile, name: str) -> None:
    """Rasm kengaytmali fayl haqiqatan rasm bo'lishi kerak (boshqa narsa yashirilmagan)."""
    try:
        with Image.open(upload) as image:
            image.verify()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise FileRejected(_("«%(name)s» rasm sifatida ochilmadi.") % {"name": name}) from exc
    finally:
        upload.seek(0)
