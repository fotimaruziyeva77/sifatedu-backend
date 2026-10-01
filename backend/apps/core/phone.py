"""O'zbekiston telefon raqamlarini yagona `+998XXXXXXXXX` formatiga keltirish."""

import re

_NON_DIGITS = re.compile(r"\D")
LOCAL_NUMBER_LENGTH = 9
COUNTRY_CODE = "998"


class InvalidPhoneError(ValueError):
    pass


def normalize_phone(value: str) -> str:
    """'+998 (90) 123-45-67', '998901234567' yoki '901234567' → '+998901234567'."""
    digits = _NON_DIGITS.sub("", value or "")
    if len(digits) == LOCAL_NUMBER_LENGTH:
        digits = COUNTRY_CODE + digits
    if len(digits) != len(COUNTRY_CODE) + LOCAL_NUMBER_LENGTH or not digits.startswith(
        COUNTRY_CODE
    ):
        raise InvalidPhoneError(value)
    return f"+{digits}"
