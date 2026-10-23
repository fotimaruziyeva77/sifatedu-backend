"""Slaydlar: Markdown → slayd (turi, ustki yozuv, sarlavha) va bloklar (matn, ro'yxat, kod
ranglari, jadval, eslatma, ustunlar, kartalar, indekslar sxemasi)."""

from typing import Any

import pytest

from apps.catalog import slides
from apps.catalog.models import Category, Course, Lesson, LessonSlides, Module


def test_split_ignores_separator_inside_code() -> None:
    text = "# Bir\n\n---\n\n```python\nx = 1\n---\ny = 2\n```\n\n---\n\nUch\n---\n"

    parts = slides.split(text)

    assert len(parts) == 3
    assert "---\ny = 2" in parts[1]
    assert parts[2] == "Uch"


def test_render_blocks() -> None:
    [slide] = slides.render(
        "## Sarlavha\n\n**Qalin** va `kod`, [havola](https://sifatedu.uz).\n\n"
        "3. uch\n4. to'rt\n   - ichki\n\n| A | B |\n|---|--:|\n| 1 | 2 |\n\n> Eslatma"
    )
    paragraph, ordered, table, quote = slide["blocks"]

    assert slide["title"] == [["t", "Sarlavha"]]
    assert slide["kind"] == "plain" and slide["kicker"] == []
    assert paragraph["inl"][0] == ["b", [["t", "Qalin"]]]
    assert ["c", "kod"] in paragraph["inl"]
    assert ["a", "https://sifatedu.uz", [["t", "havola"]]] in paragraph["inl"]
    assert ordered["t"] == "ol" and ordered["start"] == 3
    assert ordered["items"][1]["sub"]["items"][0]["inl"] == [["t", "ichki"]]
    assert table["head"] == [[["t", "A"]], [["t", "B"]]]
    assert table["rows"] == [[[["t", "1"]], [["t", "2"]]]]
    assert table["align"] == ["", "right"]
    assert quote == {"t": "quote", "blocks": [{"t": "p", "inl": [["t", "Eslatma"]]}]}


def test_slide_kinds_from_headings_and_kicker() -> None:
    cover, plain, section, practice, summary, quiz = slides.render(
        "###### Python darsi\n# List va Tuple\n\nTavsif\n\n---\n\n"
        "###### 02 · List\n## Indeks\n\nMatn\n\n---\n\n"
        "# Tuple\n\n---\n\n"
        "###### Amaliyot 1 · 10 daqiqa\n## Do'stlar\n\n1. bir\n\n---\n\n"
        "###### Xulosa va uyga vazifa\n## Bugun\n\n---\n\n"
        "###### 04 · Viktorina\n## Savollar"
    )

    assert cover["kind"] == "cover"
    assert cover["kicker"] == [["t", "Python darsi"]]
    assert cover["title"] == [["t", "List va Tuple"]]
    assert cover["blocks"] == [{"t": "p", "inl": [["t", "Tavsif"]]}]
    assert plain["kind"] == "plain" and plain["kicker"] == [["t", "02 · List"]]
    assert section["kind"] == "section"
    assert [practice["kind"], summary["kind"], quiz["kind"]] == ["practice", "summary", "quiz"]


def test_cards_group_headings_with_tone_number_and_label() -> None:
    [slide] = slides.render(
        "## Asboblar\n\n`b = [4, 5]`\n\n### Uzunlik {.sariq}\n\nlen(b) → 2\n\n"
        "### 01 Dictionary\n\nKalit va qiymat\n\n#### Kod\n\n```python\nprint(1)\n```\n\n"
        "***\n\nPastdagi izoh"
    )
    intro, grid, note = slide["blocks"]

    assert intro["t"] == "p"
    first, second, third = grid["cards"]
    assert first == {
        "title": [["t", "Uzunlik"]],
        "label": False,
        "tone": "sariq",
        "num": "",
        "blocks": [{"t": "p", "inl": [["t", "len(b) → 2"]]}],
    }
    assert (second["num"], second["title"]) == ("01", [["t", "Dictionary"]])
    assert third["label"] is True and third["blocks"][0]["t"] == "code"
    assert note == {"t": "p", "inl": [["t", "Pastdagi izoh"]]}


def test_unknown_tone_stays_in_title() -> None:
    [slide] = slides.render("### Karta {.pushti}\n\nmatn")

    assert slide["blocks"][0]["cards"][0]["title"] == [["t", "Karta {.pushti}"]]


def test_columns() -> None:
    [slide] = slides.render(
        "###### 01 · Muammo\n## Ikki usul\n\n### Noqulay {.qizil}\n\n```python\na = 1\n```\n\n"
        "|||\n\n### Qulay {.sariq}\n\nRo'yxat\n\n|||\n"
    )
    [columns] = slide["blocks"]

    assert slide["title"] == [["t", "Ikki usul"]]
    assert columns["t"] == "cols" and len(columns["cols"]) == 2
    left, right = columns["cols"]
    assert left[0]["cards"][0]["tone"] == "qizil"
    assert right[0]["cards"][0]["blocks"] == [{"t": "p", "inl": [["t", "Ro'yxat"]]}]


def test_column_separator_inside_code_is_text() -> None:
    [slide] = slides.render("```text\n|||\n```")

    assert slide["blocks"][0]["t"] == "code"


def test_index_scheme() -> None:
    [slide] = slides.render(
        '```indeks\nmevalar = ["olma", "anor", 3]\n```\n\n```indeks\nsoz = "Py"\n```\n\n'
        "```indeks\nx = open('fayl')\n```"
    )
    words, letters, broken = slide["blocks"]

    assert (words["t"], words["name"], words["chars"]) == ("index", "mevalar", False)
    assert words["items"] == ['"olma"', '"anor"', "3"]
    assert letters == {"t": "index", "name": "soz", "items": ["P", "y"], "chars": True}
    assert broken["t"] == "code" and broken["lang"] == "python"


def test_code_is_highlighted_by_line() -> None:
    [slide] = slides.render('```python\nfor i in range(3):\n    print("salom")  # izoh\n```')
    [code] = slide["blocks"]

    assert code["t"] == "code" and code["lang"] == "python"
    assert len(code["lines"]) == 2
    first, second = code["lines"]
    assert ["k", "for"] in first
    assert ["nb", "range"] in first
    assert ["s", '"salom"'] in second
    assert ["c", "# izoh"] in second
    assert "".join(text for _cls, text in second) == '    print("salom")  # izoh'


def test_unknown_language_is_plain_text() -> None:
    [slide] = slides.render("```nomalum\nbir ikki\n```")

    assert slide["blocks"][0]["lines"] == [[["", "bir ikki"]]]


def test_html_and_unsafe_links_are_text() -> None:
    [slide] = slides.render("<script>alert(1)</script>\n\n[bos](javascript:alert(1))")
    first, second = slide["blocks"]

    assert first == {"t": "p", "inl": [["t", "<script>alert(1)</script>"]]}
    assert all(node[0] != "a" or node[1] == "" for node in second["inl"])


@pytest.mark.django_db
def test_lesson_slides_are_rendered_on_save(db: Any) -> None:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="python", title_uz="Python", category=category)
    lesson = Lesson.objects.create(
        module=Module.objects.create(course=course, title_uz="M"), title_uz="D"
    )

    item = LessonSlides.objects.create(lesson=lesson, markdown="# Bir\n\n---\n\nIkki")
    assert len(item.data) == 2

    item.markdown = "Faqat bitta"
    item.save(update_fields=["markdown"])
    item.refresh_from_db()
    assert item.data == [
        {
            "kind": "plain",
            "kicker": [],
            "title": [],
            "blocks": [{"t": "p", "inl": [["t", "Faqat bitta"]]}],
        }
    ]
