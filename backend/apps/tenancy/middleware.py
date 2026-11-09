from collections.abc import Callable
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django_tenants.middleware.main import TenantMainMiddleware

from .access import has_feature
from .limits import LimitReached
from .models import Center
from .sections import feature_of_view, view_target

# Docker va monitoring ichki manzil bilan murojaat qiladi — u hech qaysi markazniki emas.
HEALTH_PATHS = ("/api/v1/health/",)
BLOCKED_MESSAGE = "Markaz xizmati vaqtincha to'xtatilgan."


def _error(code: str, message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _center_blocked(request: HttpRequest) -> HttpResponse:
    if request.path.startswith("/api/"):
        return _error("center_blocked", BLOCKED_MESSAGE, 402)
    return HttpResponse(BLOCKED_MESSAGE, status=402, content_type="text/plain; charset=utf-8")


class CenterMiddleware(TenantMainMiddleware):
    """So'rov manzili bo'yicha markaz sxemasini tanlaydi va tarifni tekshiradi.

    Noma'lum manzil — 404, to'xtatilgan markaz — 402, tarifga kirmagan bo'lim — 403.
    Ko'rinishda `open_when_blocked = True` — to'xtatilgan markazda ham javob beradi.
    """

    def get_tenant(self, domain_model: Any, hostname: str) -> Center:
        # Tarif shu so'rovning o'zida keladi: bo'lim tekshiruvi qo'shimcha so'rov qilmaydi.
        return domain_model.objects.select_related("tenant__plan").get(domain=hostname).tenant

    def process_view(
        self, request: HttpRequest, view_func: Callable[..., Any], *_args: Any
    ) -> HttpResponse | None:
        center = getattr(request, "tenant", None)
        if (
            center is not None
            and center.state == Center.State.BLOCKED
            and not getattr(view_target(view_func), "open_when_blocked", False)
        ):
            return _center_blocked(request)
        feature = feature_of_view(view_func)
        if feature and not has_feature(feature):
            return _error("feature_disabled", "Bu bo'lim markaz tarifiga kirmagan.", 403)
        return None

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        # API'da DRF o'zi javob beradi; admin panelda — sahifaga xabar bilan qaytamiz.
        if isinstance(exception, LimitReached) and not request.path.startswith("/api/"):
            messages.error(request, str(exception.detail))
            return HttpResponseRedirect(request.path)
        return None

    def no_tenant_found(self, request: HttpRequest, hostname: str) -> Any:
        if request.path in HEALTH_PATHS:
            self.setup_url_routing(request, force_public=True)
            return None
        return super().no_tenant_found(request, hostname)
