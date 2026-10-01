from django.urls import path

from . import views

urlpatterns = [
    path("shop/", views.ShopView.as_view(), name="shop"),
    path("shop/<int:pk>/buy/", views.BuyView.as_view(), name="shop-buy"),
    path("shop/orders/", views.MyPurchasesView.as_view(), name="shop-orders"),
]
