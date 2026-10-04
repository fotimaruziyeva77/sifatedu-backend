from django.urls import path

from .views import (
    DailyAnswerView,
    DailyFinishView,
    DailyOverviewView,
    DailyReviewView,
    DailyStartView,
    TeacherDailyView,
)

urlpatterns = [
    path("daily-test/", DailyOverviewView.as_view(), name="daily-test"),
    path("daily-test/<int:pk>/start/", DailyStartView.as_view(), name="daily-test-start"),
    path("daily-test/attempts/<int:pk>/", DailyReviewView.as_view(), name="daily-test-review"),
    path(
        "daily-test/attempts/<int:pk>/answers/", DailyAnswerView.as_view(), name="daily-test-answer"
    ),
    path(
        "daily-test/attempts/<int:pk>/finish/", DailyFinishView.as_view(), name="daily-test-finish"
    ),
    path("teacher/groups/<int:pk>/daily-test/", TeacherDailyView.as_view(), name="teacher-daily"),
]
