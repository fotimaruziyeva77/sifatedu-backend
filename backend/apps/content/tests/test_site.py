from typing import Any

import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.catalog.models import Course
from apps.content import models as content_models
from apps.content.models import Advantage, Concern, LegalPage, SiteSettings


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@pytest.fixture
def seeded(db: Any) -> None:
    call_command("seed_demo", verbosity=0)


def get_site(language: str = "uz") -> dict[str, Any]:
    response = APIClient().get("/api/v1/site/", HTTP_ACCEPT_LANGUAGE=language)
    assert response.status_code == 200
    return response.json()


@pytest.mark.usefixtures("seeded")
def test_site_payload_structure() -> None:
    data = get_site()

    assert data["settings"]["hero_title"] == "Kelajagingizni *kod* bilan yozing"
    assert data["settings"]["about_text"].startswith("Biz — sohada")
    assert data["settings"]["promo_video"] is None
    assert data["stats"]["courses"] == 8
    assert len(data["advantages"]) == 6
    assert len(data["concerns"]) == 6
    assert set(data["concerns"][0]) == {"id", "problem", "answer"}
    assert len(data["steps"]) == 4
    assert len(data["featured_courses"]) == 4
    assert data["featured_courses"][0]["slug"] == "sifat-kids"
    assert {page["slug"] for page in data["legal_pages"]} == {"offer", "privacy", "refund-policy"}
    # Fikrlar faqat haqiqiy bo'lsa: namunaviy ma'lumotda yo'q.
    assert data["testimonials"] == []


@pytest.mark.usefixtures("seeded")
@pytest.mark.parametrize(
    ("language", "expected"),
    [("ru", "Напишите своё будущее *кодом*"), ("en", "Write your future in *code*")],
)
def test_site_payload_is_translated(language: str, expected: str) -> None:
    assert get_site(language)["settings"]["hero_title"] == expected


@pytest.mark.usefixtures("seeded")
def test_missing_translation_falls_back_to_uzbek() -> None:
    Advantage.objects.update(title_en="")

    titles = [item["title"] for item in get_site("en")["advantages"]]

    assert titles[0] == "Istalgan vaqtda video darslar"


@pytest.mark.usefixtures("seeded")
def test_cache_is_invalidated_on_change() -> None:
    assert get_site()["settings"]["phone"] == "+998 90 000 00 00"

    site = SiteSettings.load()
    site.phone = "+998 71 111 11 11"
    site.save()

    assert get_site()["settings"]["phone"] == "+998 71 111 11 11"


@pytest.mark.usefixtures("seeded")
def test_only_published_featured_courses_are_listed() -> None:
    Course.objects.filter(slug="frontend").update(status=Course.Status.DRAFT)
    Course.objects.filter(slug="sifat-kids").update(is_featured=False)

    data = get_site()

    slugs = {course["slug"] for course in data["featured_courses"]}
    assert slugs == {"kompyuter-savodxonligi", "backend"}
    assert data["stats"]["courses"] == 7


@pytest.mark.usefixtures("seeded")
def test_unpublished_testimonials_are_hidden() -> None:
    # `Testimonial` nomi "Test" bilan boshlangani uchun pytest uni test klassi deb o'ylamasin.
    testimonial = content_models.Testimonial.objects.create(author_name="Ali", text_uz="Zo'r kurs")
    assert get_site()["testimonials"] == []

    testimonial.is_published = True
    testimonial.save()
    assert len(get_site()["testimonials"]) == 1


@pytest.mark.usefixtures("seeded")
def test_unpublished_concerns_are_hidden() -> None:
    Concern.objects.filter(order=0).update(is_published=False)

    problems = [item["problem"] for item in get_site()["concerns"]]

    assert len(problems) == 5
    assert "Qayerdan boshlashni bilmayman" not in problems


@pytest.mark.django_db
def test_seed_keeps_existing_site_texts() -> None:
    SiteSettings.load()
    SiteSettings.objects.update(hero_title_uz="O'zimizning sarlavha")

    call_command("seed_demo", verbosity=0)

    title, about = SiteSettings.objects.values_list("hero_title_uz", "about_text_uz").get()
    assert title == "O'zimizning sarlavha"
    assert about.startswith("Biz — sohada")


@pytest.mark.django_db
def test_legal_page_html_is_sanitized() -> None:
    LegalPage.objects.create(
        slug="offer",
        title_uz="Oferta",
        body_uz='<p onclick="x()">Matn</p><script>alert(1)</script><a href="javascript:x()">h</a>',
    )

    response = APIClient().get("/api/v1/pages/offer/")

    assert response.status_code == 200
    body = response.json()["body"]
    assert "<script" not in body
    assert "onclick" not in body
    assert "javascript:" not in body
    assert "<p>Matn</p>" in body


@pytest.mark.django_db
def test_unknown_legal_page_returns_404() -> None:
    response = APIClient().get("/api/v1/pages/yoq/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
