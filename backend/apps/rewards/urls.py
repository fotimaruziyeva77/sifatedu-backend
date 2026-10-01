from django.urls import path

from . import views

urlpatterns = [
    path("rewards/", views.RewardsView.as_view(), name="rewards"),
    path("rewards/history/", views.HistoryView.as_view(), name="rewards-history"),
    path("rewards/settings/", views.RewardSettingsView.as_view(), name="rewards-settings"),
    path("rewards/rating/", views.RatingView.as_view(), name="rewards-rating"),
    path("rewards/discount/", views.DiscountView.as_view(), name="rewards-discount"),
    path("teacher/penalties/", views.PenaltyListView.as_view(), name="teacher-penalties"),
    path(
        "teacher/penalties/<int:pk>/cancel/",
        views.PenaltyCancelView.as_view(),
        name="teacher-penalty-cancel",
    ),
]
