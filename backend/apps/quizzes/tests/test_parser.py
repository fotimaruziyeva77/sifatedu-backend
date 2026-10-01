"""«Tez kiritish» formati: barcha turlar, kod bloki va qator raqamli xatolar."""

import pytest

from apps.quizzes.grading import DraftChoice
from apps.quizzes.parser import ParseError, parse

from .conftest import SOURCE


def errors(source: str) -> list[str]:
    with pytest.raises(ParseError) as caught:
        parse(source)
    return caught.value.errors


def test_all_kinds_are_recognised() -> None:
    single, multiple, text, order, match = parse(SOURCE)

    assert [item.kind for item in (single, multiple, text, order, match)] == [
        "SINGLE",
        "MULTIPLE",
        "TEXT",
        "ORDER",
        "MATCH",
    ]
    assert single.text == "HTML nimaning qisqartmasi?"
    assert single.explanation == ["HTML — sahifa tuzilmasi uchun belgilash tili."]
    assert [choice.is_correct for choice in single.choices] == [True, False, False]
    assert [choice.text for choice in text.choices] == ["h1", "<h1>"]
    assert all(choice.is_correct for choice in text.choices)
    assert match.choices[0] == DraftChoice("HTML", match="tuzilma")


def test_steps_follow_their_numbers_and_code_is_kept() -> None:
    [question] = parse(
        """
        ? Natija qanday tartibda chiqadi?
        ```python
        print("a")
            print("b")  # chekinish saqlanadi
        ```
        2) Ikkinchi
        1) Birinchi
        # izoh qatori
        ---
        3) Uchinchi
        """
    )

    assert question.kind == "ORDER"
    assert [choice.text for choice in question.choices] == ["Birinchi", "Ikkinchi", "Uchinchi"]
    assert question.language == "python"
    assert question.code[0].strip() == 'print("a")'
    assert question.code[1].endswith('    print("b")  # chekinish saqlanadi')


def test_errors_name_the_line() -> None:
    found = errors(
        "+ savolsiz variant\n"
        "? \n"
        "? Aralash\n"
        "+ A\n"
        "= B\n"
        "? Bitta ham to'g'ri yo'q\n"
        "- A\n"
        "- B\n"
        "? Juft chala\n"
        "HTML ::\n"
        "? Tushunarsiz\n"
        "bu nima\n"
    )

    assert found[0] == "1-qator: avval «?» bilan savol yozing."
    assert "2-qator: savol matni bo'sh." in found
    assert "10-qator: juftning ikkala tomoni ham kerak (chap :: o'ng)." in found
    assert "12-qator: tushunarsiz qator — «bu nima»." in found
    assert any(error.startswith("3-qator: bitta savolda turli xil javoblar") for error in found)
    assert any(error.startswith("6-qator: Bitta to'g'ri javobli savolda") for error in found)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", "Birorta ham savol topilmadi."),
        ("? Kod\n```js\nlet a = 1", "Kod bloki yopilmagan (``` yetishmayapti)."),
        ("? Bitta qadam\n1. Faqat shu", "1-qator: Tartiblash uchun kamida 2 ta qadam kerak."),
        ("? Bitta variant\n+ Faqat shu", "1-qator: Kamida 2 ta variant kerak."),
        ("? Bitta juft\nA :: B", "1-qator: Moslashtirish uchun kamida 2 ta juft kerak."),
    ],
)
def test_incomplete_questions(source: str, message: str) -> None:
    assert message in errors(source)
