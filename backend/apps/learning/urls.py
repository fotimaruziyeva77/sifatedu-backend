from django.urls import path

from .teaching import TeacherGroupsView, TeacherGroupView
from .views import (
    EnrollFreeView,
    LessonKeyView,
    LessonMasterPlaylistView,
    LessonPlayerView,
    LessonProgressView,
    LessonRenditionPlaylistView,
    MyCoursesView,
    MyCourseView,
)

urlpatterns = [
    path("my/courses/", MyCoursesView.as_view(), name="my-courses"),
    path("my/courses/<slug:slug>/", MyCourseView.as_view(), name="my-course"),
    path("my/courses/<slug:slug>/enroll/", EnrollFreeView.as_view(), name="course-enroll-free"),
    path("lessons/<int:pk>/", LessonPlayerView.as_view(), name="lesson-player"),
    path("lessons/<int:pk>/progress/", LessonProgressView.as_view(), name="lesson-progress"),
    path(
        "lessons/<int:pk>/hls/master.m3u8",
        LessonMasterPlaylistView.as_view(),
        name="lesson-hls-master",
    ),
    path(
        "lessons/<int:pk>/hls/<slug:name>.m3u8",
        LessonRenditionPlaylistView.as_view(),
        name="lesson-hls-rendition",
    ),
    path("lessons/<int:pk>/hls/key", LessonKeyView.as_view(), name="lesson-hls-key"),
    path("teacher/groups/", TeacherGroupsView.as_view(), name="teacher-groups"),
    path("teacher/groups/<int:pk>/", TeacherGroupView.as_view(), name="teacher-group"),
]
