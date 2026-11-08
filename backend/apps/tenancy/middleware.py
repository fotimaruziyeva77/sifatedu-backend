from typing import Any

from django.http import HttpRequest
from django_tenants.middleware.main import TenantMainMiddleware

# Docker va monitoring ichki manzil bilan murojaat qiladi — u hech qaysi markazniki emas.
HEALTH_PATHS = ("/api/v1/health/",)


class CenterMiddleware(TenantMainMiddleware):
    """So'rov manzili bo'yicha markaz sxemasini tanlaydi. Noma'lum manzil — 404."""

    def no_tenant_found(self, request: HttpRequest, hostname: str) -> Any:
        if request.path in HEALTH_PATHS:
            self.setup_url_routing(request, force_public=True)
            return None
        return super().no_tenant_found(request, hostname)
