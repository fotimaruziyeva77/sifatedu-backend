from django.urls import path

from .views import BrandView, ClickView, EskizView, SetupView, TelegramView

urlpatterns = [
    path("setup/", SetupView.as_view(), name="center-setup"),
    path("brand/", BrandView.as_view(), name="center-brand"),
    path("telegram/", TelegramView.as_view(), name="center-telegram"),
    path("click/", ClickView.as_view(), name="center-click"),
    path("eskiz/", EskizView.as_view(), name="center-eskiz"),
]
