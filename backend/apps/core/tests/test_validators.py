import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.validators import MaxFileSizeValidator


def test_file_within_limit_passes() -> None:
    MaxFileSizeValidator(1)(SimpleUploadedFile("a.mp4", b"x" * 1024))


def test_file_over_limit_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        MaxFileSizeValidator(1)(SimpleUploadedFile("a.mp4", b"x" * (1024 * 1024 + 1)))

    assert error.value.code == "file_too_large"


def test_validator_is_comparable_for_migrations() -> None:
    assert MaxFileSizeValidator(200) == MaxFileSizeValidator(200)
    assert MaxFileSizeValidator(200) != MaxFileSizeValidator(100)
