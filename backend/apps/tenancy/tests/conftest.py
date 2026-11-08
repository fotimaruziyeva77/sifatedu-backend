from typing import Any

import pytest

from apps.tenancy.db import connection
from apps.tenancy.models import Center
from apps.tenancy.services import ensure_center

SECOND_HOST = "ikkinchi.testserver"


@pytest.fixture(scope="session")
def second_center(django_db_setup: None, django_db_blocker: Any) -> Center:
    """Sxema yaratish qimmat: butun sessiyaga bitta."""
    with django_db_blocker.unblock():
        connection.set_schema_to_public()
        return ensure_center("ikkinchi", "Ikkinchi markaz", [SECOND_HOST])
