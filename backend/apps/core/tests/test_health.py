import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_ok() -> None:
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": True, "cache": True}}


@pytest.mark.django_db
def test_api_not_found_returns_json_error() -> None:
    response = APIClient().get("/api/v1/does-not-exist/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
