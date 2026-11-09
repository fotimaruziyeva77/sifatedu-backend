from typing import Any

from tenant_schemas_celery.task import TenantTask


class CenterTask(TenantTask):
    """Markaz to'xtatilgan yoki bo'limi yopiq bo'lsa, vazifa bajarilmaydi.

    Sxema `task_prerun`da tanlangan bo'ladi. Import shu yerda: Celery bu klassni Django ilovalari
    yuklanishidan oldin oladi.
    """

    abstract = True

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        from .access import task_is_open

        if not task_is_open(self.name):
            return None
        return super().__call__(*args, **kwargs)
