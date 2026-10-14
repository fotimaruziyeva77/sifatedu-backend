"""O'quvchi rasmi (selfi yoki o'qituvchi yuklagan surat): telefon kamerasidagi katta rasm —
markazdan kesilgan kvadrat 512 px JPEG. EXIF bo'yicha buriladi (telefonda yonboshlab tushgan
rasm tik turadi), ortiqcha metama'lumot (joylashuv va h.k.) saqlanmaydi.
"""

from io import BytesIO
from typing import TYPE_CHECKING

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

if TYPE_CHECKING:
    from .models import User

SIZE = 512
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 50_000_000  # undan katta rasm ochilmaydi (xotirani to'ldiradigan "bomba")


class PhotoError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan sabab."""


def square_jpeg(data: bytes) -> ContentFile:
    if len(data) > MAX_BYTES:
        raise PhotoError("Rasm 10 MB dan katta bo'lmasin.")
    try:
        with Image.open(BytesIO(data)) as source:
            width, height = source.size
            if width * height > MAX_PIXELS:
                raise PhotoError("Rasm juda katta.")
            upright = ImageOps.exif_transpose(source) or source
            square = ImageOps.fit(upright.convert("RGB"), (SIZE, SIZE), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PhotoError("Rasmni o'qib bo'lmadi: JPG yoki PNG rasm yuboring.") from exc
    buffer = BytesIO()
    square.save(buffer, format="JPEG", quality=85, optimize=True)
    return ContentFile(buffer.getvalue(), name="avatar.jpg")


def set_avatar(user: "User", data: bytes) -> None:
    """Yangi rasm saqlanadi, eskisi o'chiriladi."""
    content = square_jpeg(data)
    old = user.avatar.name if user.avatar else ""
    user.avatar.save("avatar.jpg", content, save=False)
    user.save(update_fields=["avatar"])
    if old:
        user.avatar.storage.delete(old)


def remove_avatar(user: "User") -> None:
    if user.avatar:
        user.avatar.delete(save=False)
        user.save(update_fields=["avatar"])
