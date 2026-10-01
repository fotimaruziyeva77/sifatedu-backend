"""Sentry'ga shaxsiy ma'lumot ketmasligi."""

from typing import Any, cast

from sentry_sdk.types import Event

from apps.core.sentry import MASK, scrub_event


def test_phone_numbers_are_masked_everywhere() -> None:
    event: dict[str, Any] = {
        "message": "Kod yuborilmadi: +998901234567",
        "exception": {"values": [{"value": "SMS xato 998 90 123 45 67"}]},
        "breadcrumbs": {"values": [{"message": "login +998-90-123-45-67"}]},
        "extra": {"note": "boshqa matn"},
    }

    result = cast(dict[str, Any], scrub_event(cast(Event, event), {}))

    assert result is not None
    assert result["message"] == f"Kod yuborilmadi: {MASK}"
    assert result["exception"]["values"][0]["value"] == f"SMS xato {MASK}"
    assert result["breadcrumbs"]["values"][0]["message"] == f"login {MASK}"
    assert result["extra"] == {"note": "boshqa matn"}
