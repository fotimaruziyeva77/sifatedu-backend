"""Faqat OpenAPI sxemasi uchun: markaz va platforma yo'llari birga."""

from django.urls import URLPattern, URLResolver, include, path

from config.urls import urlpatterns as center_urlpatterns

urlpatterns: list[URLPattern | URLResolver] = [
    *center_urlpatterns,
    path("api/v1/platform/", include("apps.tenancy.platform_urls")),
]
