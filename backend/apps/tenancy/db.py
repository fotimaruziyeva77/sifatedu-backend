from typing import Any

from django.db import connection as _connection

# django-tenants ulanishga `schema_name`, `set_schema` va boshqalarni qo'shadi — stub'larda yo'q.
connection: Any = _connection
