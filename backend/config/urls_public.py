"""Platforma manzili (`public` sxema): super admin paneli, sayt API'si va sog'liq tekshiruvi."""

from django.urls import URLPattern, URLResolver, include, path

from apps.core.views import HealthView
from apps.tenancy.admin import platform_site
from apps.tenancy.views import CenterInfoView
from apps.users.views import CsrfView

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", platform_site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/center/", CenterInfoView.as_view(), name="center"),
    path("api/v1/auth/csrf/", CsrfView.as_view(), name="csrf"),
    path("api/v1/platform/", include("apps.tenancy.platform_urls")),
]

handler404 = "apps.core.views.not_found"
handler500 = "apps.core.views.server_error"
