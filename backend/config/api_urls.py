"""`/api/v1/` ostidagi barcha endpointlar."""

from django.urls import include, path

from apps.core.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("", include("apps.assistant.urls")),
    path("", include("apps.bot.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.certificates.urls")),
    path("", include("apps.content.urls")),
    path("", include("apps.exams.urls")),
    path("", include("apps.homework.urls")),
    path("", include("apps.leads.urls")),
    path("", include("apps.learning.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.quizzes.urls")),
    path("", include("apps.rewards.urls")),
    path("", include("apps.shop.urls")),
    path("", include("apps.live.urls")),
    path("", include("apps.users.urls")),
    path("", include("apps.videos.urls")),
]
