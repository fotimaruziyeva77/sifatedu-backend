"""Google va Telegram orqali kirish.

Google tokenlari haqiqiy RSA kalit bilan imzolanadi va JWKS mijozi shu kalitni qaytaradi:
shu tariqa imzo tekshiruvining o'zi ham sinaladi.
"""

import hashlib
import hmac
import time
from datetime import timedelta
from typing import Any
from unittest import mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import OneTimeCode, SocialAccount, User

GOOGLE_CLIENT_ID = "test-client.apps.googleusercontent.com"
BOT_TOKEN = "123456:TEST-BOT-TOKEN"
BOT_USERNAME = "sifatedu_bot"
PHONE = "+998901234567"
CODE = "123456"
PASSWORD = "Qizil-Olma-2026"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _setup() -> Any:
    cache.clear()
    settings = override_settings(
        GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID,
        TELEGRAM_BOT_TOKEN=BOT_TOKEN,
        TELEGRAM_BOT_USERNAME=BOT_USERNAME,
    )
    # Kod oldindan ma'lum bo'lsin; SMS yuborilishi test_auth.py'da tekshiriladi.
    with settings, mock.patch("apps.users.otp.generate_code", return_value=CODE):
        yield


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def _google_keys(rsa_key: rsa.RSAPrivateKey) -> Any:
    """JWKS so'rovi o'rniga test kaliti (tarmoqqa chiqilmaydi)."""
    signing_key = mock.Mock(key=rsa_key.public_key())
    with mock.patch(
        "apps.users.social._jwk_client.get_signing_key_from_jwt", return_value=signing_key
    ):
        yield


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def google_token(rsa_key: rsa.RSAPrivateKey, **claims: Any) -> str:
    now = int(time.time())
    payload = {
        "iss": "https://accounts.google.com",
        "aud": GOOGLE_CLIENT_ID,
        "sub": "google-user-1",
        "email": "ali@example.com",
        "email_verified": True,
        "given_name": "Ali",
        "family_name": "Valiyev",
        "iat": now,
        "exp": now + 3600,
        **claims,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256")


def telegram_payload(**overrides: Any) -> dict[str, str]:
    data = {
        "id": "555000111",
        "first_name": "Vali",
        "auth_date": str(int(time.time())),
        **overrides,
    }
    check = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return data


def google_login(client: APIClient, rsa_key: rsa.RSAPrivateKey, **claims: Any) -> Any:
    return client.post(
        "/api/v1/auth/social/google/", {"credential": google_token(rsa_key, **claims)}
    )


def test_providers_are_listed_when_configured(client: APIClient) -> None:
    response = client.get("/api/v1/auth/social/")

    assert response.json() == {
        "google_client_id": GOOGLE_CLIENT_ID,
        "telegram_bot": BOT_USERNAME,
    }


@override_settings(GOOGLE_CLIENT_ID="", TELEGRAM_BOT_USERNAME="")
def test_providers_hidden_when_not_configured(client: APIClient) -> None:
    response = client.get("/api/v1/auth/social/")

    assert response.json() == {"google_client_id": "", "telegram_bot": ""}


def test_google_first_login_asks_for_phone(client: APIClient, rsa_key: rsa.RSAPrivateKey) -> None:
    response = google_login(client, rsa_key)

    assert response.status_code == 200
    assert response.json() == {"status": "phone_required", "first_name": "Ali"}
    # Telefon berilmaguncha akkaunt yaratilmaydi.
    assert not User.objects.exists()
    assert client.get("/api/v1/me/").status_code == 403


def test_google_registration_completes_with_phone(
    client: APIClient, rsa_key: rsa.RSAPrivateKey
) -> None:
    google_login(client, rsa_key)

    response = client.post("/api/v1/auth/social/phone/", {"phone": "90 123 45 67"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["user"]["phone"] == PHONE
    user = User.objects.get()
    assert user.first_name == "Ali"
    assert user.last_name == "Valiyev"
    assert not user.has_usable_password()
    assert user.groups.filter(name="STUDENT").exists()
    assert user.terms_accepted_at is not None
    account = SocialAccount.objects.get()
    assert (account.provider, account.uid, account.email) == (
        "google",
        "google-user-1",
        "ali@example.com",
    )
    assert client.get("/api/v1/me/").status_code == 200


def test_returning_google_user_logs_in_directly(
    client: APIClient, rsa_key: rsa.RSAPrivateKey
) -> None:
    google_login(client, rsa_key)
    client.post("/api/v1/auth/social/phone/", {"phone": PHONE})
    client.post("/api/v1/auth/logout/")

    response = google_login(APIClient(), rsa_key)

    assert response.json()["status"] == "ok"
    assert User.objects.count() == 1


def test_unverified_google_email_is_not_stored(
    client: APIClient, rsa_key: rsa.RSAPrivateKey
) -> None:
    google_login(client, rsa_key, email_verified=False)
    client.post("/api/v1/auth/social/phone/", {"phone": PHONE})

    assert SocialAccount.objects.get().email == ""


@pytest.mark.parametrize(
    "claims",
    [
        pytest.param({"aud": "boshqa-client-id"}, id="boshqa_aud"),
        pytest.param({"iss": "https://evil.example.com"}, id="boshqa_iss"),
        pytest.param({"exp": int(time.time()) - 10}, id="eskirgan"),
    ],
)
def test_google_token_is_rejected(
    client: APIClient, rsa_key: rsa.RSAPrivateKey, claims: dict[str, Any]
) -> None:
    response = google_login(client, rsa_key, **claims)

    assert response.status_code == 400
    assert not User.objects.exists()


def test_google_token_signed_by_other_key_is_rejected(client: APIClient) -> None:
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    response = google_login(client, attacker_key)

    assert response.status_code == 400
    assert not User.objects.exists()


def test_telegram_login_asks_for_phone(client: APIClient) -> None:
    response = client.post("/api/v1/auth/social/telegram/", telegram_payload())

    assert response.status_code == 200
    assert response.json()["status"] == "phone_required"


def test_telegram_registration_completes(client: APIClient) -> None:
    client.post("/api/v1/auth/social/telegram/", telegram_payload(last_name="Aliyev"))

    response = client.post("/api/v1/auth/social/phone/", {"phone": PHONE})

    assert response.json()["status"] == "ok"
    account = SocialAccount.objects.get()
    assert (account.provider, account.uid) == ("telegram", "555000111")
    assert User.objects.get().get_full_name() == "Vali Aliyev"


def test_telegram_tampered_data_is_rejected(client: APIClient) -> None:
    payload = telegram_payload()
    payload["first_name"] = "Boshqa"

    response = client.post("/api/v1/auth/social/telegram/", payload)

    assert response.status_code == 400
    assert not User.objects.exists()


def test_telegram_stale_login_is_rejected(client: APIClient) -> None:
    payload = telegram_payload(auth_date=str(int(time.time()) - 600))

    response = client.post("/api/v1/auth/social/telegram/", payload)

    assert response.status_code == 400


def test_taken_phone_requires_sms_and_links_account(
    client: APIClient, rsa_key: rsa.RSAPrivateKey
) -> None:
    existing = User.objects.create_user(phone=PHONE, password=PASSWORD, first_name="Ali")
    google_login(client, rsa_key)

    asked = client.post("/api/v1/auth/social/phone/", {"phone": PHONE})
    assert asked.json() == {"status": "code_required"}
    assert SocialAccount.objects.count() == 0

    sent = client.post("/api/v1/auth/otp/", {"phone": PHONE, "purpose": "link"})
    assert sent.status_code == 200

    linked = client.post("/api/v1/auth/social/phone/", {"phone": PHONE, "code": CODE})

    assert linked.json()["status"] == "ok"
    assert User.objects.count() == 1
    assert SocialAccount.objects.get().user == existing
    assert client.get("/api/v1/me/").json()["phone"] == PHONE


def test_link_code_is_not_sent_without_pending_social(client: APIClient) -> None:
    User.objects.create_user(phone=PHONE, password=PASSWORD)

    response = client.post("/api/v1/auth/otp/", {"phone": PHONE, "purpose": "link"})

    assert response.status_code == 400
    assert not OneTimeCode.objects.exists()


def test_wrong_link_code_does_not_link(client: APIClient, rsa_key: rsa.RSAPrivateKey) -> None:
    User.objects.create_user(phone=PHONE, password=PASSWORD)
    google_login(client, rsa_key)
    client.post("/api/v1/auth/social/phone/", {"phone": PHONE})
    client.post("/api/v1/auth/otp/", {"phone": PHONE, "purpose": "link"})

    response = client.post("/api/v1/auth/social/phone/", {"phone": PHONE, "code": "000000"})

    assert response.status_code == 400
    assert not SocialAccount.objects.exists()
    assert client.get("/api/v1/me/").status_code == 403


def test_phone_step_expires(client: APIClient, rsa_key: rsa.RSAPrivateKey) -> None:
    google_login(client, rsa_key)
    stale = (timezone.now() - timedelta(minutes=20)).timestamp()
    session = client.session
    session["pending_social"] = {**session["pending_social"], "at": stale}
    session.save()

    response = client.post("/api/v1/auth/social/phone/", {"phone": PHONE})

    assert response.status_code == 400
    assert not User.objects.exists()


def test_phone_step_requires_social_login(client: APIClient) -> None:
    response = client.post("/api/v1/auth/social/phone/", {"phone": PHONE})

    assert response.status_code == 400


def test_blocked_account_cannot_be_linked(client: APIClient, rsa_key: rsa.RSAPrivateKey) -> None:
    User.objects.create_user(phone=PHONE, password=PASSWORD, is_active=False)
    google_login(client, rsa_key)

    response = client.post("/api/v1/auth/social/phone/", {"phone": PHONE})

    assert response.status_code == 400
    assert "phone" in response.json()["error"]["fields"]


def test_provider_does_not_overwrite_user_edits(
    client: APIClient, rsa_key: rsa.RSAPrivateKey
) -> None:
    google_login(client, rsa_key)
    client.post("/api/v1/auth/social/phone/", {"phone": PHONE})
    client.patch("/api/v1/me/", {"first_name": "Alisher"}, format="json")
    client.post("/api/v1/auth/logout/")

    google_login(APIClient(), rsa_key)

    assert User.objects.get().first_name == "Alisher"


def test_avatar_is_downloaded_from_provider(
    client: APIClient, rsa_key: rsa.RSAPrivateKey, django_capture_on_commit_callbacks: Any
) -> None:
    picture = "https://lh3.googleusercontent.com/a/photo=s96-c"
    google_login(client, rsa_key, picture=picture)

    with (
        mock.patch("apps.users.tasks.fetch_social_avatar.delay") as fetch,
        django_capture_on_commit_callbacks(execute=True),
    ):
        client.post("/api/v1/auth/social/phone/", {"phone": PHONE})

    assert fetch.call_args.args[1] == picture
