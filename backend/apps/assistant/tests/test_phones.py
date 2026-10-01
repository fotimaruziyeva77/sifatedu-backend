"""Telefon raqamlari AI'ga ketmaydi: belgi bilan almashtiriladi va faqat backend'da ochiladi."""

import pytest

from apps.assistant.phones import hide_cards, mask_phones, resolve, unmask


@pytest.mark.parametrize(
    "text",
    [
        "Raqamim +998 90 123 45 67",
        "raqamim 998901234567",
        "(90) 123-45-67 ga qo'ng'iroq qiling",
        "901234567",
        "+998(90)1234567",
    ],
)
def test_uzbek_numbers_are_masked(text: str) -> None:
    phones: dict[str, str] = {}

    masked = mask_phones(text, phones)

    assert "‹telefon-1›" in masked
    assert "123" not in masked
    assert phones == {"1": "+998901234567"}


def test_same_number_gets_same_placeholder() -> None:
    phones: dict[str, str] = {}

    first = mask_phones("90 123 45 67", phones)
    second = mask_phones("yana: +998901234567 va 91 765 43 21", phones)

    assert first == "‹telefon-1›"
    assert second == "yana: ‹telefon-1› va ‹telefon-2›"
    assert phones == {"1": "+998901234567", "2": "+998917654321"}


def test_prices_and_short_numbers_stay() -> None:
    phones: dict[str, str] = {}

    assert mask_phones("Narxi 1 200 000 so'm, 18 dars", phones) == "Narxi 1 200 000 so'm, 18 dars"
    assert phones == {}


def test_card_numbers_are_hidden() -> None:
    assert hide_cards("karta 8600 1234 5678 9012") == "karta ‹karta raqami yashirildi›"


def test_resolve_accepts_only_numbers_client_gave() -> None:
    phones = {"1": "+998901234567", "akkaunt": "+998935556677"}

    assert resolve("‹telefon-1›", phones) == "+998901234567"
    assert resolve("‹telefon-akkaunt›", phones) == "+998935556677"
    assert resolve("+998 90 123 45 67", phones) == "+998901234567"
    # AI o'ylab topgan raqam yoki mavjud bo'lmagan belgi — rad etiladi.
    assert resolve("+998 99 111 22 33", phones) is None
    assert resolve("‹telefon-7›", phones) is None


def test_unmask_for_display() -> None:
    assert unmask("Raqamingiz ‹telefon-1› yozib olindi", {"1": "+998901234567"}) == (
        "Raqamingiz +998901234567 yozib olindi"
    )
