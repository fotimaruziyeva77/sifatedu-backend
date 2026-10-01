import pytest

from apps.core.phone import InvalidPhoneError, normalize_phone


@pytest.mark.parametrize(
    "value",
    ["+998901234567", "998901234567", "901234567", "+998 (90) 123-45-67", " 90 123 45 67 "],
)
def test_normalize_phone(value: str) -> None:
    assert normalize_phone(value) == "+998901234567"


@pytest.mark.parametrize("value", ["", "12345", "+7 912 345 67 89", "+99890123456789"])
def test_invalid_phone(value: str) -> None:
    with pytest.raises(InvalidPhoneError):
        normalize_phone(value)
