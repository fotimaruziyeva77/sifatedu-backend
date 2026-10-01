from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.notifications import sms


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@override_settings(SMS_DRY_RUN=True)
def test_dry_run_does_not_call_provider(caplog: Any) -> None:
    with mock.patch("apps.notifications.sms._post") as post:
        sms.send_sms("+998901234567", "Sifat Edu: kod 123456")

    post.assert_not_called()
    assert "123456" in caplog.text


@override_settings(SMS_DRY_RUN=False, ESKIZ_EMAIL="", ESKIZ_PASSWORD="")
def test_missing_credentials_raise() -> None:
    with pytest.raises(sms.SmsNotConfiguredError):
        sms.send_sms("+998901234567", "matn")


@override_settings(SMS_DRY_RUN=False, ESKIZ_EMAIL="a@b.uz", ESKIZ_PASSWORD="parol")
def test_token_is_refreshed_once_on_401() -> None:
    responses = [
        (200, {"data": {"token": "eski"}}),
        (401, {"message": "Expired"}),
        (200, {"data": {"token": "yangi"}}),
        (200, {"id": "1", "status": "waiting"}),
    ]
    with mock.patch("apps.notifications.sms._post", side_effect=responses) as post:
        sms.send_sms("+998901234567", "matn")

    last_path, last_data, last_token = post.call_args.args
    assert last_path == "/message/sms/send"
    assert last_data["mobile_phone"] == "998901234567"
    assert last_token == "yangi"
    assert cache.get(sms.TOKEN_CACHE_KEY) == "yangi"


@override_settings(SMS_DRY_RUN=False, ESKIZ_EMAIL="a@b.uz", ESKIZ_PASSWORD="parol")
def test_provider_error_is_raised_for_retry() -> None:
    cache.set(sms.TOKEN_CACHE_KEY, "token")
    with (
        mock.patch("apps.notifications.sms._post", return_value=(500, {})),
        pytest.raises(RuntimeError),
    ):
        sms.send_sms("+998901234567", "matn")
