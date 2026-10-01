from django.urls import path

from .views import LoginLinkView, QuizLinkView, WebhookView

urlpatterns = [
    path("bot/webhook/", WebhookView.as_view(), name="bot-webhook"),
    path("bot/quizzes/<int:pk>/link/", QuizLinkView.as_view(), name="bot-quiz-link"),
    path("bot/login/<str:token>/", LoginLinkView.as_view(), name="bot-login"),
]
