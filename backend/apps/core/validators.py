from django.core.exceptions import ValidationError
from django.core.files import File
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class MaxFileSizeValidator:
    """Yuklanadigan fayl hajmini cheklaydi (megabaytda)."""

    def __init__(self, megabytes: int) -> None:
        self.megabytes = megabytes

    def __call__(self, file: File) -> None:
        if file.size and file.size > self.megabytes * 1024 * 1024:
            raise ValidationError(
                _("Fayl hajmi %(limit)s MB dan oshmasin."),
                code="file_too_large",
                params={"limit": self.megabytes},
            )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, MaxFileSizeValidator) and other.megabytes == self.megabytes

    def __hash__(self) -> int:
        return hash(self.megabytes)
