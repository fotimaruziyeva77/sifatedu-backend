from django.urls import path

from .views import ChatRateView, ChatView

urlpatterns = [
    path("assistant/chat/", ChatView.as_view(), name="assistant-chat"),
    path("assistant/chat/rate/", ChatRateView.as_view(), name="assistant-chat-rate"),
]
