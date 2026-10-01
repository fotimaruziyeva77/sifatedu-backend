from django.urls import path

from .views import (
    HomeworkSubmitView,
    MyHomeworkView,
    ReviewDetailView,
    ReviewListView,
    SubmissionWithdrawView,
)

urlpatterns = [
    path("homework/", MyHomeworkView.as_view(), name="my-homework"),
    path("homework/<int:pk>/submissions/", HomeworkSubmitView.as_view(), name="homework-submit"),
    path(
        "homework/submissions/<int:pk>/",
        SubmissionWithdrawView.as_view(),
        name="homework-withdraw",
    ),
    path("teacher/reviews/", ReviewListView.as_view(), name="teacher-reviews"),
    path("teacher/reviews/<int:pk>/", ReviewDetailView.as_view(), name="teacher-review"),
]
