from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import OneTimeCode, User
from apps.users.roles import Role

PHONE = "+998901234567"
CODE = "123456"
PASSWORD = "Qizil-Olma-2026"


@pytest.fixture(autouse=True)
def _setup(db: Any) -> Any:
    cache.clear()
    # Kod oldindan ma'lum bo'lsin; SMS yuborilishi alohida tekshiriladi.
    with mock.patch("apps.users.otp.generate_code", return_value=CODE):
        yield


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db: Any) -> User:
    return User.objects.create_user(phone=PHONE, password=PASSWORD, first_name="Ali")


def request_code(client: APIClient, purpose: str, phone: str = PHONE) -> Any:
    return client.post("/api/v1/auth/otp/", {"phone": phone, "purpose": purpose})


def register(client: APIClient, **overrides: Any) -> Any:
    payload = {
        "phone": PHONE,
        "code": CODE,
        "first_name": "Ali",
        "last_name": "Valiyev",
        "password": PASSWORD,
        "accept_terms": True,
        **overrides,
    }
    return client.post("/api/v1/auth/register/", payload)


def test_register_flow(client: APIClient) -> None:
    sent = request_code(client, "register", phone="90 123 45 67")
    assert sent.status_code == 200
    assert sent.json() == {"resend_in": 60}

    response = register(client)

    assert response.status_code == 201
    assert response.json()["phone"] == PHONE
    user = User.objects.get(phone=PHONE)
    assert user.check_password(PASSWORD)
    assert user.groups.filter(name=Role.STUDENT).exists()
    assert user.terms_accepted_at is not None
    # Aksiyalarga rozilik alohida va oldindan berilmaydi.
    assert user.marketing_consent_at is None
    assert client.get("/api/v1/me/").json()["first_name"] == "Ali"


def test_register_with_marketing_consent(client: APIClient) -> None:
    request_code(client, "register")

    response = register(client, marketing_consent=True)

    assert response.status_code == 201
    assert User.objects.get(phone=PHONE).marketing_consent_at is not None


def test_register_remembers_who_invited(client: APIClient) -> None:
    from apps.users.services import REFERRAL_COOKIE, referral_code

    friend = User.objects.create_user(phone="+998907770000", password=PASSWORD)
    code = referral_code(friend)
    request_code(client, "register")
    # Sayt havolasidagi `?ref=` ni frontend cookie'ga yozadi (proxy.ts).
    client.cookies[REFERRAL_COOKIE] = code.lower()

    response = register(client)

    assert response.status_code == 201
    assert User.objects.get(phone=PHONE).referred_by == friend
    assert response.cookies[REFERRAL_COOKIE].value == ""


def test_unknown_referral_code_is_ignored(client: APIClient) -> None:
    request_code(client, "register")
    client.cookies["sifat_ref"] = "NOPE2345"

    assert register(client).status_code == 201
    assert User.objects.get(phone=PHONE).referred_by is None


def test_code_sms_is_sent_in_request_language(
    client: APIClient, django_capture_on_commit_callbacks: Any
) -> None:
    with (
        mock.patch("apps.notifications.tasks.send_sms") as send,
        django_capture_on_commit_callbacks(execute=True),
    ):
        client.post(
            "/api/v1/auth/otp/",
            {"phone": PHONE, "purpose": "register"},
            HTTP_ACCEPT_LANGUAGE="ru",
        )

    phone, text = send.call_args.args
    assert phone == PHONE
    assert CODE in text
    assert "код" in text


def test_code_is_stored_only_as_hash(client: APIClient) -> None:
    request_code(client, "register")

    stored = OneTimeCode.objects.get(phone=PHONE)
    assert CODE not in stored.code_hash
    assert len(stored.code_hash) == 64


def test_registered_phone_cannot_request_register_code(client: APIClient, user: User) -> None:
    response = request_code(client, "register")

    assert response.status_code == 400
    assert "phone" in response.json()["error"]["fields"]


def test_code_resend_cooldown(client: APIClient) -> None:
    assert request_code(client, "register").status_code == 200

    response = request_code(client, "register")

    assert response.status_code == 429
    error = response.json()["error"]
    assert error["code"] == "otp_cooldown"
    assert 0 < error["retry_after"] <= 60


def test_daily_code_limit(client: APIClient) -> None:
    for _index in range(5):
        OneTimeCode.objects.create(
            phone=PHONE,
            purpose="register",
            code_hash="x" * 64,
            expires_at=timezone.now(),
        )

    response = request_code(client, "register")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "otp_daily_limit"


def test_wrong_code_closes_after_five_attempts(client: APIClient) -> None:
    request_code(client, "register")
    for _attempt in range(5):
        assert register(client, code="000000").status_code == 400

    # Kod yopildi: to'g'ri kod ham endi o'tmaydi.
    response = register(client)

    assert response.status_code == 400
    assert "code" in response.json()["error"]["fields"]
    assert not User.objects.filter(phone=PHONE).exists()


def test_expired_code_is_rejected(client: APIClient) -> None:
    request_code(client, "register")
    OneTimeCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

    assert register(client).status_code == 400


def test_weak_password_does_not_spend_code(client: APIClient) -> None:
    request_code(client, "register")

    weak = register(client, password="12345678")
    assert weak.status_code == 400
    assert "password" in weak.json()["error"]["fields"]

    assert register(client).status_code == 201


def test_terms_must_be_accepted(client: APIClient) -> None:
    request_code(client, "register")

    response = register(client, accept_terms=False)

    assert response.status_code == 400
    assert "accept_terms" in response.json()["error"]["fields"]


def test_login_and_logout(client: APIClient, user: User) -> None:
    response = client.post("/api/v1/auth/login/", {"phone": "901234567", "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["phone"] == PHONE
    assert client.get("/api/v1/me/").status_code == 200

    assert client.post("/api/v1/auth/logout/").status_code == 204
    assert client.get("/api/v1/me/").status_code == 403


@pytest.mark.parametrize(
    ("phone", "password"), [(PHONE, "noto'g'ri-parol"), ("+998909999999", PASSWORD)]
)
def test_login_error_does_not_reveal_account(
    client: APIClient, user: User, phone: str, password: str
) -> None:
    response = client.post("/api/v1/auth/login/", {"phone": phone, "password": password})

    assert response.status_code == 400
    assert "non_field_errors" in response.json()["error"]["fields"]


def test_inactive_user_cannot_login(client: APIClient, user: User) -> None:
    User.objects.filter(pk=user.pk).update(is_active=False)

    response = client.post("/api/v1/auth/login/", {"phone": PHONE, "password": PASSWORD})

    assert response.status_code == 400


def test_login_is_locked_after_ten_failures(client: APIClient, user: User) -> None:
    for _attempt in range(10):
        client.post("/api/v1/auth/login/", {"phone": PHONE, "password": "xato-parol"})

    response = client.post("/api/v1/auth/login/", {"phone": PHONE, "password": PASSWORD})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "login_locked"


def test_login_requires_csrf_token(user: User) -> None:
    client = APIClient(enforce_csrf_checks=True)
    payload = {"phone": PHONE, "password": PASSWORD}

    assert client.post("/api/v1/auth/login/", payload).status_code == 403

    client.get("/api/v1/auth/csrf/")
    token = client.cookies["csrftoken"].value
    response = client.post("/api/v1/auth/login/", payload, HTTP_X_CSRFTOKEN=token)

    assert response.status_code == 200


def test_reset_for_unknown_phone_looks_the_same(client: APIClient) -> None:
    response = request_code(client, "reset")

    assert response.status_code == 200
    assert response.json() == {"resend_in": 60}
    assert not OneTimeCode.objects.exists()


def test_password_reset_signs_out_other_sessions(user: User) -> None:
    other_device = APIClient()
    other_device.post("/api/v1/auth/login/", {"phone": PHONE, "password": PASSWORD})
    assert other_device.get("/api/v1/me/").status_code == 200

    client = APIClient()
    request_code(client, "reset")
    new_password = "Yangi-Parol-2026"
    response = client.post(
        "/api/v1/auth/password/reset/",
        {"phone": PHONE, "code": CODE, "password": new_password},
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(new_password)
    assert client.get("/api/v1/me/").status_code == 200
    assert other_device.get("/api/v1/me/").status_code == 403


def test_reset_code_is_single_use(client: APIClient, user: User) -> None:
    request_code(client, "reset")
    payload = {"phone": PHONE, "code": CODE, "password": "Yangi-Parol-2026"}

    assert client.post("/api/v1/auth/password/reset/", payload).status_code == 200
    assert client.post("/api/v1/auth/password/reset/", payload).status_code == 400


def test_password_reset_unlocks_login(client: APIClient, user: User) -> None:
    for _attempt in range(10):
        client.post("/api/v1/auth/login/", {"phone": PHONE, "password": "xato-parol"})
    request_code(client, "reset")
    new_password = "Yangi-Parol-2026"
    client.post(
        "/api/v1/auth/password/reset/",
        {"phone": PHONE, "code": CODE, "password": new_password},
    )

    response = APIClient().post("/api/v1/auth/login/", {"phone": PHONE, "password": new_password})

    assert response.status_code == 200
