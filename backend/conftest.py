"""Testlar markaz sxemasida ishlaydi: `testserver` manzili shu markazniki."""

from typing import Any

import pytest

from apps.tenancy.db import connection

TEST_SCHEMA = "test_center"


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup: None, django_db_blocker: Any) -> None:
    from apps.tenancy.services import ensure_center, ensure_platform

    with django_db_blocker.unblock():
        connection.set_schema_to_public()
        ensure_platform("platform.testserver")
        ensure_center(TEST_SCHEMA, "Test markaz", ["testserver"])


@pytest.fixture(autouse=True)
def _center_schema() -> None:
    # Avvalgi test boshqa manzilga so'rov yuborgan bo'lishi mumkin.
    connection.set_schema(TEST_SCHEMA)
