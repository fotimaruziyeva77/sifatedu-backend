"""Baholash qoidalari va yulduzlar."""

from typing import Any

import pytest

from apps.quizzes.grading import grade, normalize
from apps.quizzes.models import Choice, Question
from apps.quizzes.services import stars_for


def question(kind: str, *choices: dict[str, Any]) -> tuple[Question, list[Choice]]:
    item = Question(pk=1, kind=kind, text="?")
    return item, [Choice(pk=index, order=index, **data) for index, data in enumerate(choices, 1)]


@pytest.mark.parametrize(
    ("raw", "clean"),
    [("  <H1>. ", "<h1>"), ("Hyper  Text\tMarkup!", "hyper text markup"), ("?!", "")],
)
def test_normalize(raw: str, clean: str) -> None:
    assert normalize(raw) == clean


def test_text_answer_accepts_listed_variants_only() -> None:
    item, choices = question("TEXT", {"text": "h1"}, {"text": "<h1>"})

    assert grade(item, choices, {"text": "H1"})
    assert grade(item, choices, {"text": " <h1>. "})
    assert not grade(item, choices, {"text": "h 1"})
    assert not grade(item, choices, {"text": ""})


def test_multiple_needs_exact_set() -> None:
    item, choices = question(
        "MULTIPLE",
        {"text": "a", "is_correct": True},
        {"text": "b", "is_correct": True},
        {"text": "c"},
    )

    assert grade(item, choices, {"choices": [2, 1]})
    assert not grade(item, choices, {"choices": [1]})
    assert not grade(item, choices, {"choices": [1, 2, 3]})


def test_match_needs_every_pair() -> None:
    item, choices = question("MATCH", {"text": "a", "match": "1"}, {"text": "b", "match": "2"})

    assert grade(item, choices, {"pairs": {"1": 1, "2": 2}})
    assert not grade(item, choices, {"pairs": {"1": 1}})
    assert not grade(item, choices, {"pairs": {"1": 2, "2": 1}})


@pytest.mark.parametrize(
    ("score", "pass_percent", "stars"),
    [
        (100, 70, 3),
        (90, 70, 3),
        (89, 70, 2),
        (70, 70, 2),
        (69, 70, 1),
        (50, 70, 1),
        (49, 70, 0),
        # O'tish bali 95% bo'lsa, 92% — o'tmadi: 3 yulduz emas.
        (92, 95, 1),
        (95, 95, 3),
        (45, 40, 2),
    ],
)
def test_stars(score: int, pass_percent: int, stars: int) -> None:
    assert stars_for(score, pass_percent) == stars
