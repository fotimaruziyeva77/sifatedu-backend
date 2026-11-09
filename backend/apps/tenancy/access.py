"""Hozirgi markaz: ochiq bo'limlar va holat."""

from django.utils import timezone
from rest_framework import exceptions

from .db import connection
from .models import Center
from .sections import ALWAYS_RUN_TASKS, feature_of_task, features_of_app, features_of_perm

EXPIRY_WARNING_DAYS = 7


class FeatureClosed(exceptions.APIException):
    status_code = 403
    default_code = "feature_disabled"
    default_detail = "Bu bo'lim markaz tarifiga kirmagan."


def current_center() -> Center | None:
    tenant = connection.tenant
    if isinstance(tenant, Center):
        return tenant
    # `schema_context` ichida va platformada `tenant` — faqat sxema nomi.
    return Center.objects.select_related("plan").filter(schema_name=connection.schema_name).first()


def has_feature(feature: str) -> bool:
    center = current_center()
    return center is None or feature in center.features


def require_feature(feature: str) -> None:
    if not has_feature(feature):
        raise FeatureClosed


def days_until_expiry() -> int | None:
    """Obuna tugashiga necha kun (o'tgan bo'lsa manfiy). Muddat uzoq yoki yo'q bo'lsa — None."""
    center = current_center()
    if center is None or center.paid_until is None:
        return None
    left = (center.paid_until - timezone.localdate()).days
    return left if left <= EXPIRY_WARNING_DAYS else None


def _any_open(features: tuple[str, ...]) -> bool:
    return not features or any(has_feature(feature) for feature in features)


def perm_is_open(perm: str) -> bool:
    return _any_open(features_of_perm(perm))


def app_is_open(app_label: str) -> bool:
    return _any_open(features_of_app(app_label))


def task_is_open(name: str) -> bool:
    """To'xtatilgan markaz va yopiq bo'lim vazifalari bajarilmaydi."""
    if name in ALWAYS_RUN_TASKS:
        return True
    center = current_center()
    if center is None:
        return True
    feature = feature_of_task(name)
    return center.state != Center.State.BLOCKED and (feature is None or feature in center.features)
