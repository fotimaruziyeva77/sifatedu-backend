"""Telefon raqamlari AI'ga yuborilmaydi (TZ 4.9).

Mijoz yozgan raqam `‹telefon-1›` belgisiga almashtiriladi, haqiqiy raqam suhbatning `phones`
maydonida qoladi. Ariza yaratilganda backend belgini raqamga aylantiradi — shuning uchun AI
raqamni ko'rmaydi ham, o'ylab topa ham olmaydi.
"""

import re

from apps.core.phone import InvalidPhoneError, normalize_phone

# +998 90 123 45 67, (90) 123-45-67, 998901234567, 901234567 ...
PHONE_RE = re.compile(
    r"(?<![\d+])"
    r"(?:\+?\s?998[\s\-]*)?"
    r"\(?\d{2}\)?[\s\-]*"
    r"\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
    r"(?!\d)"
)
# Bank kartasi (Uzcard, Humo, Visa — 16 raqam): chatda umuman saqlanmaydi.
CARD_RE = re.compile(r"(?<!\d)(?:\d{4}[ \-]?){3}\d{4}(?!\d)")
PLACEHOLDER_RE = re.compile(r"‹telefon-(\d+|akkaunt)›")

ACCOUNT_KEY = "akkaunt"
CARD_MASK = "‹karta raqami yashirildi›"


def placeholder(key: str) -> str:
    return f"‹telefon-{key}›"


def hide_cards(text: str) -> str:
    return CARD_RE.sub(CARD_MASK, text)


def mask_phones(text: str, phones: dict[str, str]) -> str:
    """Matndagi raqamlarni belgiga almashtiradi; yangi raqamlar `phones`ga qo'shiladi."""

    def replace(match: re.Match[str]) -> str:
        try:
            phone = normalize_phone(match.group(0))
        except InvalidPhoneError:
            return match.group(0)
        for key, known in phones.items():
            if known == phone:
                return placeholder(key)
        key = str(sum(1 for known_key in phones if known_key.isdigit()) + 1)
        phones[key] = phone
        return placeholder(key)

    return PHONE_RE.sub(replace, text)


def resolve(value: str, phones: dict[str, str]) -> str | None:
    """AI bergan qiymat → haqiqiy raqam. Faqat mijozning o'zi bergan raqam qabul qilinadi."""
    match = PLACEHOLDER_RE.search(value or "")
    if match:
        return phones.get(match.group(1))
    try:
        phone = normalize_phone(value)
    except InvalidPhoneError:
        return None
    return phone if phone in phones.values() else None


def unmask(text: str, phones: dict[str, str]) -> str:
    """Mijozga ko'rsatishda belgini raqamning o'ziga qaytaradi."""
    return PLACEHOLDER_RE.sub(lambda match: phones.get(match.group(1), match.group(0)), text)
