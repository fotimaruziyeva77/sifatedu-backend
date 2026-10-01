from django.urls import path

from .views import ClickCompleteView, ClickPrepareView, OrderCreateView, OrderDetailView

urlpatterns = [
    path("orders/", OrderCreateView.as_view(), name="order-list"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("payments/click/prepare/", ClickPrepareView.as_view(), name="click-prepare"),
    path("payments/click/complete/", ClickCompleteView.as_view(), name="click-complete"),
]
