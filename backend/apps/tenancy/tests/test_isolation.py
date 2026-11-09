"""Bir markaz boshqasiga o'tmasligi: so'rov, sessiya, kesh, fayl, vazifa, rejali vazifa."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django_tenants.utils import schema_context, schema_exists
from rest_framework.test import APIClient
from tenant_schemas_celery.scheduler import TenantAwareScheduler

from apps.catalog.models import Category, Course
from apps.tenancy.db import connection
from apps.tenancy.management.commands import adopt_center
from apps.tenancy.models import Center, Plan
from apps.tenancy.services import ensure_center
from apps.tenancy.storage import CenterS3Storage, center_prefix
from apps.users.models import User
from apps.videos import s3
from config.celery import app

from .conftest import SECOND_HOST

pytestmark = pytest.mark.django_db

FIRST_HOST = "testserver"
PLATFORM_HOST = "platform.testserver"
COURSES = "/api/v1/courses/"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def publish_course(schema: str, slug: str) -> None:
    with schema_context(schema):
        category = Category.objects.create(slug=slug, name_uz=slug)
        Course.objects.create(
            slug=slug, title_uz=slug, category=category, status=Course.Status.PUBLISHED
        )


def course_slugs(client: APIClient, **host: Any) -> list[str]:
    response = client.get(COURSES, **host)
    assert response.status_code == 200
    return [course["slug"] for course in response.json()["results"]]


# --- So'rov qaysi markazga tushadi ---


def test_center_sees_only_its_own_courses(client: APIClient, second_center: Center) -> None:
    publish_course(connection.schema_name, "birinchi")
    publish_course(second_center.schema_name, "ikkinchi")

    assert course_slugs(client, HTTP_HOST=FIRST_HOST) == ["birinchi"]
    assert course_slugs(client, HTTP_HOST=SECOND_HOST) == ["ikkinchi"]


def test_ssr_request_is_routed_by_forwarded_host(client: APIClient, second_center: Center) -> None:
    publish_course(second_center.schema_name, "ikkinchi")

    slugs = course_slugs(client, HTTP_HOST="backend:8000", HTTP_X_FORWARDED_HOST=SECOND_HOST)

    assert slugs == ["ikkinchi"]


def test_www_prefix_is_the_same_center(client: APIClient, second_center: Center) -> None:
    publish_course(second_center.schema_name, "ikkinchi")

    assert course_slugs(client, HTTP_HOST=f"www.{SECOND_HOST}") == ["ikkinchi"]


def test_unknown_host_is_not_found(client: APIClient) -> None:
    assert client.get(COURSES, HTTP_HOST="begona.testserver").status_code == 404


def test_health_answers_on_internal_address(client: APIClient) -> None:
    assert client.get("/api/v1/health/", HTTP_HOST="localhost:8000").status_code == 200


def test_platform_host_has_no_center_api(client: APIClient) -> None:
    assert client.get(COURSES, HTTP_HOST=PLATFORM_HOST).status_code == 404


# --- Kirish ---


@pytest.mark.parametrize("engine", ["db", "cached_db"])
def test_login_does_not_carry_over_to_another_center(
    client: APIClient, second_center: Center, settings: Any, engine: str
) -> None:
    settings.SESSION_ENGINE = f"django.contrib.sessions.backends.{engine}"
    client.force_login(User.objects.create_user(phone="+998901112233", first_name="Ali"))

    assert client.get("/api/v1/me/", HTTP_HOST=FIRST_HOST).status_code == 200
    assert client.get("/api/v1/me/", HTTP_HOST=SECOND_HOST).status_code in {401, 403}


@pytest.fixture
def platform_client(client: APIClient) -> APIClient:
    with schema_context("public"):
        client.force_login(User.objects.create_superuser(phone="+998900000001"))
    return client


def test_platform_panel_lists_centers(platform_client: APIClient) -> None:
    response = platform_client.get("/admin/tenancy/center/", HTTP_HOST=PLATFORM_HOST)

    assert response.status_code == 200
    assert "Test markaz" in response.content.decode()


def test_platform_panel_keeps_schema_read_only(platform_client: APIClient) -> None:
    center = Center.objects.exclude(schema_name="public").first()
    assert center is not None

    response = platform_client.get(
        f"/admin/tenancy/center/{center.pk}/change/", HTTP_HOST=PLATFORM_HOST
    )

    assert response.status_code == 200
    assert 'name="schema_name"' not in response.content.decode()


@pytest.mark.parametrize("path", ["/admin/", "/admin/tenancy/center/add/"])
def test_platform_panel_pages_open(platform_client: APIClient, path: str) -> None:
    assert platform_client.get(path, HTTP_HOST=PLATFORM_HOST).status_code == 200


def center_form(schema: str) -> dict[str, Any]:
    return {
        "name": "Yangi markaz",
        "schema_name": schema,
        "plan": Plan.objects.get(name="Start").pk,
        "domains-TOTAL_FORMS": 1,
        "domains-INITIAL_FORMS": 0,
        "domains-MIN_NUM_FORMS": 0,
        "domains-MAX_NUM_FORMS": 1000,
        "domains-0-domain": "yangi.testserver",
        "domains-0-is_primary": "on",
    }


def test_platform_panel_creates_center(platform_client: APIClient) -> None:
    response = platform_client.post(
        "/admin/tenancy/center/add/",
        center_form("yangi"),
        format="multipart",
        HTTP_HOST=PLATFORM_HOST,
    )

    assert response.status_code == 302
    assert schema_exists("yangi")
    assert Center.objects.get(schema_name="yangi").domains.get().domain == "yangi.testserver"


def test_platform_panel_rejects_bad_schema_name(platform_client: APIClient) -> None:
    response = platform_client.post(
        "/admin/tenancy/center/add/",
        center_form('x"; DROP SCHEMA public; --'),
        format="multipart",
        HTTP_HOST=PLATFORM_HOST,
    )

    assert response.status_code == 200
    assert not Center.objects.filter(name="Yangi markaz").exists()


def test_center_admin_has_no_platform_pages(client: APIClient) -> None:
    client.force_login(User.objects.create_superuser(phone="+998900000002"))

    assert client.get("/admin/tenancy/center/", HTTP_HOST=FIRST_HOST).status_code == 404


def test_center_login_does_not_open_platform_panel(client: APIClient) -> None:
    client.force_login(User.objects.create_superuser(phone="+998900000003"))

    response = client.get("/admin/tenancy/center/", HTTP_HOST=PLATFORM_HOST)

    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


# --- Kesh va fayllar ---


def test_cache_is_separate(second_center: Center) -> None:
    first = connection.schema_name
    cache.set("kalit", "birinchi")

    with schema_context(second_center.schema_name):
        assert cache.get("kalit") is None
        cache.set("kalit", "ikkinchi")

    with schema_context(first):
        assert cache.get("kalit") == "birinchi"


def test_files_stay_inside_center_folder(second_center: Center) -> None:
    storage = CenterS3Storage(bucket_name="b", custom_domain="media.test", querystring_auth=False)

    with schema_context(second_center.schema_name):
        assert storage.url("rasm/a.png") == "https://media.test/centers/ikkinchi/rasm/a.png"
        assert storage._normalize_name("../../sifat/a.png") == "centers/ikkinchi/sifat/a.png"
        assert s3.object_key("videos/1/a.ts") == "centers/ikkinchi/videos/1/a.ts"


def test_first_center_files_are_not_moved(settings: Any) -> None:
    settings.LEGACY_STORAGE_SCHEMAS = [connection.schema_name]

    assert center_prefix() == ""


# --- Vazifalar ---


@app.task(name="tenancy_tests.current_schema")
def current_schema() -> str:
    return str(connection.schema_name)


def test_task_is_sent_with_center_schema(second_center: Center) -> None:
    with patch("celery.Celery.send_task") as send, schema_context(second_center.schema_name):
        app.send_task("tenancy_tests.current_schema")

    assert send.call_args.kwargs["headers"]["_schema_name"] == second_center.schema_name


def test_worker_runs_task_in_sender_schema(second_center: Center) -> None:
    first = connection.schema_name

    result = current_schema.apply(headers={"_schema_name": second_center.schema_name})

    assert result.get() == second_center.schema_name
    assert connection.schema_name == first


def scheduled_for(entry_name: str) -> list[str]:
    """Rejali vazifa qaysi sxemalarga yuboriladi."""
    scheduler = TenantAwareScheduler(app=app, lazy=True)
    entries = scheduler._tenant_aware_beat_schedule_to_dict(settings.CELERY_BEAT_SCHEDULE)
    entry = scheduler.Entry(name=entry_name, app=app, **entries[entry_name])
    sent: list[str] = []

    def remember(*_args: Any, **_kwargs: Any) -> MagicMock:
        sent.append(connection.schema_name)
        return MagicMock()

    with patch.object(scheduler, "apply_async", side_effect=remember):
        scheduler.apply_entry(entry)
    return sent


def test_scheduled_task_runs_once_per_center(second_center: Center) -> None:
    centers = Center.objects.exclude(schema_name="public").values_list("schema_name", flat=True)

    sent = scheduled_for("expire-orders@__all_tenants_only__")

    assert sorted(sent) == sorted(centers)


def test_server_check_runs_once_for_the_whole_server(second_center: Center) -> None:
    assert scheduled_for("check-server-resources@public") == ["public"]


# --- Baza ---


def test_trigram_extension_is_visible_to_every_center() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace "
            "WHERE e.extname = 'pg_trgm'"
        )
        assert cursor.fetchone() == ("public",)


def test_ensure_center_is_repeatable(second_center: Center) -> None:
    again = ensure_center(second_center.schema_name, "Boshqa nom", [SECOND_HOST])

    assert again.pk == second_center.pk
    assert again.domains.count() == 1


def test_migrated_database_passes_adopt_check() -> None:
    call_command("adopt_center", "--check")


def test_legacy_database_is_not_migrated() -> None:
    legacy = {"r": ["users_user", "catalog_course"]}

    with (
        patch.object(adopt_center, "public_relations", return_value=legacy),
        pytest.raises(CommandError, match="adopt_center"),
    ):
        call_command("adopt_center", "--check")
