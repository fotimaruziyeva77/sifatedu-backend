"""Sentry: xatolar monitoringi. Shaxsiy ma'lumot (telefon, parol, kod) yuborilmaydi."""

import re
from typing import Any, cast

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber
from sentry_sdk.types import Event, Hint

# O'zbekiston raqamlari: +998 90 123 45 67 ko'rinishidagi har qanday yozuv.
PHONE = re.compile(r"\+?998[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")
MASK = "[telefon]"

# Standart ro'yxatga loyihaga xos kalitlar qo'shiladi.
EXTRA_DENYLIST = ["phone", "code", "otp", "sign_string", "sealed_key", "credential"]


def _mask(value: Any) -> Any:
    if isinstance(value, str):
        return PHONE.sub(MASK, value)
    if isinstance(value, dict):
        return {key: _mask(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask(item) for item in value]
    return value


def scrub_event(event: Event, hint: Hint) -> Event | None:
    """Xabar, istisno matni va breadcrumb'lardagi telefon raqamlarini yashiradi."""
    data = cast(dict[str, Any], event)
    for key in ("message", "logentry", "exception", "breadcrumbs", "extra", "tags"):
        if key in data:
            data[key] = _mask(data[key])
    return event


def init_sentry(dsn: str, environment: str, traces_sample_rate: float) -> None:
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        # So'rov tanasi yuborilmaydi: kirish formasida telefon va parol bor.
        max_request_body_size="never",
        event_scrubber=EventScrubber(denylist=DEFAULT_DENYLIST + EXTRA_DENYLIST),
        before_send=scrub_event,
    )
