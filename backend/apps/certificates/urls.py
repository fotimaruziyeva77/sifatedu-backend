from django.urls import path

from .views import MyCertificatesView, VerifyView

urlpatterns = [
    path("certificates/", MyCertificatesView.as_view(), name="my-certificates"),
    path("certificates/<str:number>/", VerifyView.as_view(), name="certificate-verify"),
]
