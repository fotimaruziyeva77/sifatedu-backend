"""Platforma manzili (`public` sxema): super admin paneli va sog'liq tekshiruvi."""

from django.urls import URLPattern, URLResolver, path

from apps.core.views import HealthView
from apps.tenancy.admin import platform_site

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", platform_site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
]

handler404 = "apps.core.views.not_found"
handler500 = "apps.core.views.server_error"
