from django.urls import path

from .views import (
    NotificationListView,
    NotificationReadView,
    NotificationSettingsView,
    TelegramConnectView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/read/", NotificationReadView.as_view(), name="notifications-read"),
    path("me/notifications/", NotificationSettingsView.as_view(), name="me-notifications"),
    path("me/telegram/connect/", TelegramConnectView.as_view(), name="me-telegram-connect"),
]
