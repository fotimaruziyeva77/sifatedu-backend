from django.urls import path

from .views import LegalPageView, SiteView

urlpatterns = [
    path("site/", SiteView.as_view(), name="site"),
    path("pages/<slug:slug>/", LegalPageView.as_view(), name="legal-page"),
]
