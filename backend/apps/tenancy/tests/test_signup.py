"""Markazni egasi o'zi ochadi: tariflar, manzil, SMS kod, tayyorlash va birinchi kirish."""

from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context, schema_exists
from rest_framework.test import APIClient

from apps.tenancy import signup as flow
from apps.tenancy import tasks
from apps.tenancy.db import connection
from apps.tenancy.models import Center, Plan, Signup
from apps.users.models import OneTimeCode, User
from apps.users.roles import Role, role_names

pytestmark = pytest.mark.django_db

PLATFORM: dict[str, Any] = {"HTTP_HOST": "platform.testserver"}
PLANS = "/api/v1/platform/plans/"
ADDRESS = "/api/v1/platform/address/"
SIGNUPS = "/api/v1/platform/signups/"
CODE = "123456"
PHONE = "+998901112233"
SLUG = "najot-talim"
HOST: dict[str, Any] = {"HTTP_HOST": f"{SLUG}.testserver"}


@pytest.fixture(autouse=True)
def _known_code() -> Iterator[None]:
    cache.clear()
    with patch("apps.users.otp.generate_code", return_value=CODE):
        yield


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def sms() -> Iterator[MagicMock]:
    with patch("apps.notifications.tasks.send_sms_task.delay") as send:
        yield send


@pytest.fixture
def plan() -> Plan:
    return Plan.objects.get(name="Standart")


def data(plan: Plan, **changes: Any) -> dict[str, Any]:
    return {
        "plan": plan.pk,
        "name": "Najot Ta'lim",
        "slug": SLUG,
        "first_name": "Aziz",
        "last_name": "Karimov",
        "phone": PHONE,
        "password": "Yaxshi-parol-77",
        **changes,
    }


def start(client: APIClient, plan: Plan, capture: Any, **changes: Any) -> Any:
    with capture(execute=True):
        return client.post(SIGNUPS, data(plan, **changes), format="json", **PLATFORM)


# --- Tariflar va manzil ---


def test_only_public_plans_are_listed(client: APIClient) -> None:
    Plan.objects.create(name="Maxfiy", is_public=False)

    response = client.get(PLANS, **PLATFORM)

    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert names == ["Start", "Standart", "Pro"]
    assert response.json()[1]["features"] == ["lessons", "bot", "click"]
    assert response.json()[0]["trial_days"] == 14


@pytest.mark.parametrize(
    ("slug", "available", "reason"),
    [
        ("najot", True, "free"),
        ("NAJOT", True, "free"),
        ("ab", False, "invalid"),
        ("1abc", False, "invalid"),
        ("ab--cd", False, "invalid"),
        ("abc-", False, "invalid"),
        ("a_b", False, "invalid"),
        ("admin", False, "reserved"),
        ("media", False, "reserved"),
        ("sifat", False, "reserved"),
    ],
)
def test_address_rules(client: APIClient, slug: str, available: bool, reason: str) -> None:
    body = client.get(ADDRESS, {"slug": slug}, **PLATFORM).json()

    assert body == {"available": available, "reason": reason}


def test_address_is_taken_by_existing_domain(client: APIClient, second_center: Center) -> None:
    assert client.get(ADDRESS, {"slug": "ikkinchi"}, **PLATFORM).json()["reason"] == "taken"


def test_schema_name_cannot_hit_postgres_names() -> None:
    assert flow.schema_for("pg-catalog") == "c_pg_catalog"
    assert flow.schema_for("public") == "c_public"


def test_platform_api_is_closed_on_center_address(client: APIClient) -> None:
    assert client.get(PLANS, HTTP_HOST="testserver").status_code == 404


# --- Ariza ---


def test_signup_sends_code_and_keeps_no_plain_password(
    client: APIClient, plan: Plan, sms: MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    response = start(client, plan, django_capture_on_commit_callbacks)

    assert response.status_code == 201
    signup = Signup.objects.get(token=response.json()["token"])
    assert signup.status == Signup.Status.PENDING
    assert check_password("Yaxshi-parol-77", signup.password_hash)
    assert sms.call_args.args == (
        PHONE,
        f"Test platforma: tasdiqlash kodi {CODE}. Uni hech kimga aytmang.",
    )
    assert OneTimeCode.objects.filter(phone=PHONE, purpose=OneTimeCode.Purpose.SIGNUP).exists()


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"name": "A<b>"}, "name"),
        ({"name": "Bilim {x}"}, "name"),
        ({"name": "A & B"}, "name"),
        ({"slug": "admin"}, "slug"),
        ({"phone": "123"}, "phone"),
        ({"password": "123"}, "password"),
    ],
)
def test_bad_signup_is_rejected(
    client: APIClient, plan: Plan, changes: dict[str, str], field: str
) -> None:
    response = client.post(SIGNUPS, data(plan, **changes), format="json", **PLATFORM)

    assert response.status_code == 400
    assert field in response.json()["error"]["fields"]
    assert not Signup.objects.exists()


def test_hidden_plan_cannot_be_chosen(client: APIClient) -> None:
    hidden = Plan.objects.create(name="Maxfiy", is_public=False)

    response = client.post(SIGNUPS, data(hidden), format="json", **PLATFORM)

    assert response.status_code == 400


def test_repeat_signup_does_not_cancel_the_first(
    client: APIClient, plan: Plan, sms: MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    first = start(client, plan, django_capture_on_commit_callbacks)
    second = start(client, plan, django_capture_on_commit_callbacks, name="Yangi nom")

    assert second.status_code == 201
    assert first.json()["token"] != second.json()["token"]
    # Raqamni bilgan begona odam birinchi arizani bekor qila olmaydi.
    assert Signup.objects.filter(status=Signup.Status.PENDING).count() == 2
    # Kod yaqinda yuborilgan: ikkinchisi yuborilmaydi, eskisi amal qiladi.
    assert second.json()["resend_in"] > 0
    sms.assert_called_once()


def test_wrong_code_does_not_start_preparing(
    client: APIClient, plan: Plan, sms: MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    token = start(client, plan, django_capture_on_commit_callbacks).json()["token"]

    response = client.post(
        f"{SIGNUPS}{token}/verify/", {"code": "000000"}, format="json", **PLATFORM
    )

    assert response.status_code == 400
    assert "code" in response.json()["error"]["fields"]
    assert Signup.objects.get().status == Signup.Status.PENDING


def test_owner_of_a_center_cannot_get_second_trial(
    client: APIClient,
    plan: Plan,
    sms: MagicMock,
    second_center: Center,
    django_capture_on_commit_callbacks: Any,
) -> None:
    Center.objects.filter(pk=second_center.pk).update(owner_phone=PHONE)
    token = start(client, plan, django_capture_on_commit_callbacks).json()["token"]

    response = client.post(f"{SIGNUPS}{token}/verify/", {"code": CODE}, format="json", **PLATFORM)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "phone_taken"


def test_address_taken_while_confirming(
    client: APIClient, plan: Plan, sms: MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    token = start(client, plan, django_capture_on_commit_callbacks).json()["token"]
    Signup.objects.create(
        plan=plan,
        name="Boshqa",
        slug=SLUG,
        first_name="B",
        phone="+998907778899",
        status=Signup.Status.PREPARING,
    )

    response = client.post(f"{SIGNUPS}{token}/verify/", {"code": CODE}, format="json", **PLATFORM)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "address_taken"


def test_failed_preparation_frees_the_address(plan: Plan) -> None:
    signup = Signup.objects.create(
        plan=plan,
        name="Nosoz",
        slug="nosoz",
        first_name="A",
        phone="+998905556677",
        password_hash="x",
        status=Signup.Status.PREPARING,
    )

    with (
        patch("apps.tenancy.tasks.flow.provision", side_effect=RuntimeError("baza")),
        patch("apps.tenancy.tasks.flow.discard") as discard,
        patch("apps.tenancy.tasks.alert") as alert,
    ):
        tasks.provision_center(signup.pk)
    discard.assert_called_once()

    signup.refresh_from_db()
    assert signup.status == Signup.Status.FAILED
    assert signup.password_hash == ""
    assert flow.address_problem("nosoz") is None
    alert.assert_called_once()


def test_old_unfinished_signups_are_purged(plan: Plan) -> None:
    old = Signup.objects.create(
        plan=plan, name="Eski", slug="eski", first_name="A", phone="+998905556600"
    )
    Signup.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=8))
    fresh = Signup.objects.create(
        plan=plan, name="Yangi", slug="yangi", first_name="A", phone="+998905556601"
    )

    tasks.purge_signups()

    assert list(Signup.objects.all()) == [fresh]


# --- To'liq yo'l ---


def test_center_opens_and_owner_gets_in(
    client: APIClient, plan: Plan, sms: MagicMock, django_capture_on_commit_callbacks: Any
) -> None:
    token = start(client, plan, django_capture_on_commit_callbacks).json()["token"]

    with django_capture_on_commit_callbacks(execute=True):
        verified = client.post(
            f"{SIGNUPS}{token}/verify/", {"code": CODE}, format="json", **PLATFORM
        )

    assert verified.status_code == 200
    signup = Signup.objects.get(token=token)
    assert signup.status == Signup.Status.READY
    assert signup.password_hash == ""
    center = signup.center
    assert center is not None
    assert center.schema_name == "c_najot_talim"
    assert center.domains.get().domain == f"{SLUG}.testserver"
    assert center.plan == plan
    assert center.is_trial
    assert center.paid_until == timezone.localdate() + timedelta(days=14)
    assert (center.owner_name, center.owner_phone) == ("Aziz Karimov", PHONE)

    with schema_context(center.schema_name):
        owner = User.objects.get(phone=PHONE)
        assert owner.is_staff
        assert role_names(owner) == {Role.ADMIN, Role.DIRECTOR}

    info = client.get("/api/v1/center/", **HOST).json()
    assert info["name"] == "Najot Ta'lim"
    assert info["kind"] == "center"
    assert info["trial"] is True
    assert info["flagship"] is False
    assert info["features"] == ["bot", "click", "lessons"]

    site = client.get("/api/v1/site/", **HOST).json()
    assert site["settings"]["hero_title"] == "Najot Ta'lim"

    # Holat ekrani bir martalik kirish havolasini oladi.
    status = client.get(f"{SIGNUPS}{token}/", **PLATFORM).json()
    assert status["status"] == "ready"
    path = urlparse(status["url"]).path
    browser = APIClient()
    welcome = browser.get(path, **HOST)
    assert welcome.status_code == 302
    assert welcome["Location"] == "/uz/dashboard/center"
    assert welcome["Referrer-Policy"] == "no-referrer"
    assert browser.get("/api/v1/me/", **HOST).json()["phone"] == PHONE

    again = APIClient().get(path, **HOST)
    assert again.status_code == 302
    assert again["Location"] == "/uz/auth/login"

    # Egasining paroli — ro'yxatdan o'tgandagisi.
    login = APIClient().post(
        "/api/v1/auth/login/",
        {"phone": PHONE, "password": "Yaxshi-parol-77"},
        format="json",
        **HOST,
    )
    assert login.status_code == 200

    # Bir xil raqam yana sinov ololmaydi, manzil band.
    assert client.get(ADDRESS, {"slug": SLUG}, **PLATFORM).json()["reason"] == "taken"


def test_stuck_preparation_is_failed_later(plan: Plan) -> None:
    signup = Signup.objects.create(
        plan=plan,
        name="Qotgan",
        slug="qotgan",
        first_name="A",
        phone="+998905556688",
        status=Signup.Status.PREPARING,
    )
    Signup.objects.filter(pk=signup.pk).update(updated_at=timezone.now() - timedelta(minutes=20))

    with patch("apps.tenancy.tasks.alert"):
        tasks.fail_stuck_signups()

    signup.refresh_from_db()
    assert signup.status == Signup.Status.FAILED


def test_discard_drops_a_half_built_center(plan: Plan) -> None:
    schema = flow.schema_for("yarim")
    signup = Signup.objects.create(
        plan=plan, name="Yarim", slug="yarim", first_name="A", phone="+998905550001"
    )
    with schema_context(get_public_schema_name()):
        center = Center(schema_name=schema, name="Yarim")
        center.auto_create_schema = False
        center.save()
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA "{schema}"')

        flow.discard(signup)

    assert not Center.objects.filter(schema_name=schema).exists()
    assert not schema_exists(schema)


def test_signup_is_closed_until_enabled(client: APIClient, plan: Plan, settings: Any) -> None:
    settings.SIGNUP_OPEN = False

    response = client.post(SIGNUPS, data(plan), format="json", **PLATFORM)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "signup_closed"
    assert not Signup.objects.exists()
    assert client.get("/api/v1/center/", **PLATFORM).json()["signup_open"] is False


def test_existing_center_is_never_taken_over(plan: Plan) -> None:
    with schema_context(get_public_schema_name()):
        old = Center(schema_name=flow.schema_for("eski"), name="Eski markaz")
        old.auto_create_schema = False
        old.save()
        signup = Signup.objects.create(
            plan=plan,
            name="Begona",
            slug="eski",
            first_name="A",
            phone="+998905550002",
            status=Signup.Status.PREPARING,
        )

        flow.discard(signup)
        with pytest.raises(RuntimeError):
            flow.provision(signup)

    old.refresh_from_db()
    assert (old.name, old.owner_phone, old.plan) == ("Eski markaz", "", None)
