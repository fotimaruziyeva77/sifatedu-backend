"""Admin panelning o'zbekcha matnlari: locale/uz (.po → .mo Python'da yig'iladi)."""

import gettext
import io
from html import unescape

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import translation

from apps.core import po
from apps.users.models import User
from apps.users.roles import Role, set_roles


def test_compiled_catalog_matches_the_po_file() -> None:
    files = po.po_files()

    assert files, "locale/*/LC_MESSAGES/*.po topilmadi"
    for po_path in files:
        # Eskirgan bo'lsa: python manage.py compile_po
        assert po_path.with_suffix(".mo").read_bytes() == po.compiled(po_path), po_path


def test_parser_reads_plurals_multiline_and_skips_fuzzy() -> None:
    messages = po.parse(
        "\n".join(
            [
                'msgid ""',
                'msgstr ""',
                '"Language: uz\\n"',
                '"Plural-Forms: nplurals=1; plural=0;\\n"',
                "",
                'msgid "%(counter)s result"',
                'msgid_plural "%(counter)s results"',
                'msgstr[0] "%(counter)s ta natija"',
                "",
                'msgid ""',
                '"Ikki\\n"',
                '"qator"',
                'msgstr "Two lines"',
                "",
                "#, fuzzy",
                'msgid "Draft"',
                'msgstr "Qoralama"',
                "",
                'msgid "Empty"',
                'msgstr ""',
            ]
        )
    )

    assert messages == {
        "": "Language: uz\nPlural-Forms: nplurals=1; plural=0;\n",
        "%(counter)s result\0%(counter)s results": "%(counter)s ta natija",
        "Ikki\nqator": "Two lines",
    }
    catalog = gettext.GNUTranslations(io.BytesIO(po.compile_messages(messages)))
    assert (
        catalog.ngettext("%(counter)s result", "%(counter)s results", 7) == "%(counter)s ta natija"
    )
    assert catalog.gettext("Ikki\nqator") == "Two lines"


@pytest.mark.parametrize(
    ("msgid", "expected"),
    [
        ("Search apps and models...", "Bo'limlarni qidirish..."),
        ("All applications", "Barcha bo'limlar"),
        # Django'ning o'zbekcha tarjimasidagi xatolar tuzatilgan.
        ("Add %(name)s", "%(name)s qo'shish"),
        ("Clear", "Tozalash"),
        # Django'dagi to'g'ri tarjimalar o'zgarmaydi.
        ("Save", "Saqlash"),
    ],
)
def test_admin_texts_are_uzbek(msgid: str, expected: str) -> None:
    with translation.override("uz"):
        assert translation.gettext(msgid) == expected


@pytest.mark.django_db
def test_admin_is_uzbek_whatever_the_browser_language() -> None:
    admin = User.objects.create_user(phone="+998909000001", password="x", first_name="Admin")
    set_roles(admin, [Role.ADMIN])
    client = Client()
    client.force_login(admin)

    page = client.get(reverse("admin:index"), HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    html = unescape(page.content.decode())
    assert page["Content-Language"] == "uz"
    assert "Bo'limlarni qidirish" in html and "Barcha bo'limlar" in html
    assert "Search apps and models" not in html
    # Sayt API'si avvalgidek brauzer tilida.
    site = Client().get("/api/v1/site/", HTTP_ACCEPT_LANGUAGE="ru")
    assert site["Content-Language"] == "ru"
