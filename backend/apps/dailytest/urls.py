from django.urls import path

from .views import DailyOverviewView, DailyReviewView, TeacherDailyView

urlpatterns = [
    path("daily-test/", DailyOverviewView.as_view(), name="daily-test"),
    path("daily-test/attempts/<int:pk>/", DailyReviewView.as_view(), name="daily-test-review"),
    path("teacher/groups/<int:pk>/daily-test/", TeacherDailyView.as_view(), name="teacher-daily"),
]
