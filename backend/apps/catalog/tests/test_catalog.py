from typing import Any

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Instructor, Lesson, Module

pytestmark = pytest.mark.django_db

# seed_demo'dagi kurslar soni (apps/content/management/commands/seed_demo.py).
SEEDED_COURSES = 8


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def seeded(db: Any) -> None:
    call_command("seed_demo", verbosity=0)


def courses(client: APIClient, **params: Any) -> dict[str, Any]:
    response = client.get("/api/v1/courses/", params)
    assert response.status_code == 200
    return dict(response.json())


def slugs(payload: dict[str, Any]) -> list[str]:
    return [course["slug"] for course in payload["results"]]


@pytest.mark.usefixtures("seeded")
def test_course_list_shows_published_only(client: APIClient) -> None:
    Course.objects.filter(slug="ingliz-tili").update(status=Course.Status.DRAFT)

    payload = courses(client)

    assert payload["count"] == SEEDED_COURSES - 1
    assert "ingliz-tili" not in slugs(payload)


@pytest.mark.usefixtures("seeded")
def test_course_card_has_program_totals(client: APIClient) -> None:
    card = next(c for c in courses(client, page_size=50)["results"] if c["slug"] == "frontend")

    assert card["lesson_count"] == 18
    assert card["total_duration_min"] == 18 * 20
    assert card["category"]["slug"] == "dasturlash"


@pytest.mark.usefixtures("seeded")
def test_filter_by_category_and_level(client: APIClient) -> None:
    assert slugs(courses(client, category="tillar")) == ["ingliz-tili"]

    advanced = courses(client, level=Course.Level.ADVANCED)

    assert slugs(advanced) == ["suniy-intellekt"]


@pytest.mark.usefixtures("seeded")
def test_filter_by_audience(client: APIClient) -> None:
    """Bolalar kursi kattalar katalogida chiqmaydi va aksincha."""
    assert slugs(courses(client, audience=Course.Audience.KIDS)) == ["sifat-kids"]
    assert "sifat-kids" not in slugs(courses(client, audience=Course.Audience.ADULT, page_size=50))


@pytest.mark.usefixtures("seeded")
def test_filter_by_free_and_price(client: APIClient) -> None:
    Course.objects.filter(slug="kompyuter-savodxonligi").update(is_free=True, price_online=0)

    assert slugs(courses(client, is_free=True)) == ["kompyuter-savodxonligi"]
    assert "kompyuter-savodxonligi" not in slugs(courses(client, is_free=False, page_size=50))
    # Narx onlayn (bir martalik) qiymat bo'yicha filtrlanadi.
    assert set(slugs(courses(client, price_max=900_000))) == {
        "kompyuter-savodxonligi",
        "ingliz-tili",
    }
    assert slugs(courses(client, price_min=2_000_000)) == ["suniy-intellekt"]


@pytest.mark.usefixtures("seeded")
def test_filter_by_study_format(client: APIClient) -> None:
    Course.objects.filter(slug="ingliz-tili").update(study_format=Course.Format.OFFLINE)

    assert slugs(courses(client, study_format=Course.Format.OFFLINE)) == ["ingliz-tili"]


@pytest.mark.usefixtures("seeded")
def test_filter_by_video_language(client: APIClient) -> None:
    Course.objects.filter(slug="backend").update(video_language="ru")

    assert slugs(courses(client, video_language="ru")) == ["backend"]


@pytest.mark.usefixtures("seeded")
def test_search_matches_title_in_current_language(client: APIClient) -> None:
    found = client.get("/api/v1/courses/", {"q": "грамотность"}, HTTP_ACCEPT_LANGUAGE="ru").json()

    assert [course["slug"] for course in found["results"]] == ["kompyuter-savodxonligi"]


@pytest.mark.usefixtures("seeded")
def test_search_falls_back_to_uzbek(client: APIClient) -> None:
    # Ruscha sahifada o'zbekcha nom bilan qidirilsa ham kurs topiladi.
    found = client.get("/api/v1/courses/", {"q": "Praktikum"}, HTTP_ACCEPT_LANGUAGE="ru").json()

    assert "praktikum-frontend" in [course["slug"] for course in found["results"]]


@pytest.mark.usefixtures("seeded")
def test_search_without_match_returns_empty(client: APIClient) -> None:
    assert courses(client, q="kosmonavtika")["count"] == 0


@pytest.mark.usefixtures("seeded")
def test_sorting(client: APIClient) -> None:
    by_price = courses(client, sort="price", page_size=50)
    prices = [course["price_online"] for course in by_price["results"]]

    assert prices == sorted(prices)
    assert slugs(courses(client, sort="-price"))[0] == "suniy-intellekt"


@pytest.mark.usefixtures("seeded")
def test_pagination(client: APIClient) -> None:
    payload = courses(client, page_size=2)

    assert len(payload["results"]) == 2
    assert payload["count"] == SEEDED_COURSES
    assert payload["next"]


@pytest.mark.usefixtures("seeded")
def test_categories_list_counts_published_only(client: APIClient) -> None:
    Course.objects.filter(slug="ingliz-tili").update(status=Course.Status.ARCHIVED)

    response = client.get("/api/v1/categories/")

    assert response.status_code == 200
    data = {item["slug"]: item["course_count"] for item in response.json()}
    # Bo'sh qolgan kategoriya filtrlarda ko'rinmaydi.
    assert "tillar" not in data
    assert data == {"bolalar": 1, "savodxonlik": 1, "dasturlash": 3, "praktikum": 2}


@pytest.mark.usefixtures("seeded")
def test_course_detail_has_program(client: APIClient) -> None:
    response = client.get("/api/v1/courses/frontend/")

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Frontend dasturlash"
    assert data["modules"][0]["title"] == "HTML: sahifaning skeleti"
    first_lesson = data["modules"][0]["lessons"][0]
    assert first_lesson["title"] == "Birinchi veb-sahifa"
    assert first_lesson["is_preview"] is True
    assert first_lesson["duration_min"] == 20


@pytest.mark.usefixtures("seeded")
def test_course_detail_shows_both_prices(client: APIClient) -> None:
    data = client.get("/api/v1/courses/sifat-kids/").json()

    assert data["study_format"] == Course.Format.BOTH
    assert data["price_online"] == 1_200_000
    assert data["price_offline_monthly"] == 500_000
    assert (data["age_min"], data["age_max"]) == (7, 11)
    assert data["audience"] == Course.Audience.KIDS


@pytest.mark.usefixtures("seeded")
def test_course_detail_is_translated(client: APIClient) -> None:
    response = client.get("/api/v1/courses/kompyuter-savodxonligi/", HTTP_ACCEPT_LANGUAGE="ru")

    data = response.json()
    assert data["title"] == "Компьютерная грамотность"
    assert data["modules"][0]["title"] == "Компьютер и операционная система"


@pytest.mark.usefixtures("seeded")
def test_unpublished_course_detail_returns_404(client: APIClient) -> None:
    Course.objects.filter(slug="backend").update(status=Course.Status.DRAFT)

    response = client.get("/api/v1/courses/backend/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.usefixtures("seeded")
def test_unpublished_instructor_is_hidden(client: APIClient) -> None:
    mentor = Instructor.objects.create(slug="ustoz", full_name="Ustoz", is_published=False)
    Course.objects.get(slug="frontend").instructors.add(mentor)

    response = client.get("/api/v1/courses/frontend/")

    assert response.json()["instructors"] == []


def test_program_totals_follow_lessons(db: Any) -> None:
    category = Category.objects.create(slug="test", name_uz="Test")
    course = Course.objects.create(
        slug="dasturlash", title_uz="Dasturlash", category=category, status=Course.Status.PUBLISHED
    )
    module = Module.objects.create(course=course, title_uz="Modul")

    lesson = Lesson.objects.create(module=module, title_uz="Dars", duration_min=30)
    course.refresh_from_db()
    assert (course.lesson_count, course.total_duration_min) == (1, 30)

    Lesson.objects.create(module=module, title_uz="Ikkinchi", duration_min=15)
    course.refresh_from_db()
    assert (course.lesson_count, course.total_duration_min) == (2, 45)

    lesson.delete()
    course.refresh_from_db()
    assert (course.lesson_count, course.total_duration_min) == (1, 15)

    module.delete()
    course.refresh_from_db()
    assert (course.lesson_count, course.total_duration_min) == (0, 0)
