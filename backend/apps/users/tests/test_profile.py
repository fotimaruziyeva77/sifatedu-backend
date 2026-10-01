import io
from typing import Any

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.users.models import User

PHONE = "+998901234567"
PASSWORD = "Qizil-Olma-2026"


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@pytest.fixture
def user(db: Any) -> User:
    return User.objects.create_user(phone=PHONE, password=PASSWORD, first_name="Ali")


@pytest.fixture
def client(user: User) -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/login/", {"phone": PHONE, "password": PASSWORD})
    return client


def image_file(image_format: str = "PNG", size: tuple[int, int] = (16, 16)) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", size, "#e31e24").save(buffer, format=image_format)
    extension = image_format.lower()
    return SimpleUploadedFile(
        f"avatar.{extension}", buffer.getvalue(), content_type=f"image/{extension}"
    )


def test_profile_requires_login(db: Any) -> None:
    assert APIClient().get("/api/v1/me/").status_code == 403


def test_update_name_and_language(client: APIClient) -> None:
    response = client.patch(
        "/api/v1/me/", {"first_name": " Vali ", "last_name": "Aliyev", "locale": "ru"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Vali Aliyev"
    assert data["locale"] == "ru"


def test_phone_cannot_be_changed(client: APIClient) -> None:
    client.patch("/api/v1/me/", {"phone": "+998909999999"})

    assert User.objects.filter(phone=PHONE).exists()


def test_avatar_upload_and_remove(client: APIClient, user: User) -> None:
    uploaded = client.patch("/api/v1/me/", {"avatar": image_file()}, format="multipart")

    assert uploaded.status_code == 200
    assert uploaded.json()["avatar"]
    user.refresh_from_db()
    stored_name = user.avatar.name
    assert stored_name.startswith("avatars/")
    assert PHONE not in stored_name

    removed = client.patch("/api/v1/me/", {"avatar": None}, format="json")

    assert removed.status_code == 200
    assert removed.json()["avatar"] is None
    assert not user.avatar.storage.exists(stored_name)


def test_avatar_must_be_small_image(client: APIClient) -> None:
    gif = client.patch("/api/v1/me/", {"avatar": image_file("GIF")}, format="multipart")
    assert gif.status_code == 400

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("apps.users.serializers.AVATAR_MAX_BYTES", 10)
        large = client.patch("/api/v1/me/", {"avatar": image_file()}, format="multipart")
    assert large.status_code == 400


def test_password_change_keeps_current_session_only(client: APIClient, user: User) -> None:
    other_device = APIClient()
    other_device.post("/api/v1/auth/login/", {"phone": PHONE, "password": PASSWORD})

    response = client.post(
        "/api/v1/me/password/",
        {"current_password": PASSWORD, "password": "Yangi-Parol-2026"},
    )

    assert response.status_code == 204
    assert client.get("/api/v1/me/").status_code == 200
    assert other_device.get("/api/v1/me/").status_code == 403


def test_password_change_checks_current_password(client: APIClient) -> None:
    response = client.post(
        "/api/v1/me/password/",
        {"current_password": "xato", "password": "Yangi-Parol-2026"},
    )

    assert response.status_code == 400
    assert "current_password" in response.json()["error"]["fields"]
