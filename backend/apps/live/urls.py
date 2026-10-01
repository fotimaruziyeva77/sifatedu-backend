from django.urls import path

from .views import (
    JoinView,
    ScheduleView,
    TeacherAttendanceView,
    TeacherCancelView,
    TeacherCoverView,
    TeacherLessonView,
)

urlpatterns = [
    path("live/", ScheduleView.as_view(), name="live-schedule"),
    path("live/<int:pk>/join/", JoinView.as_view(), name="live-join"),
    path("teacher/live/<int:pk>/", TeacherLessonView.as_view(), name="teacher-live"),
    path(
        "teacher/live/<int:pk>/attendance/",
        TeacherAttendanceView.as_view(),
        name="teacher-live-attendance",
    ),
    path("teacher/live/<int:pk>/cancel/", TeacherCancelView.as_view(), name="teacher-live-cancel"),
    path("teacher/live/<int:pk>/covered/", TeacherCoverView.as_view(), name="teacher-live-covered"),
]
