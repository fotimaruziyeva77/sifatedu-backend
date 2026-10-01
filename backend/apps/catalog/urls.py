from django.urls import path

from .views import CategoryListView, CourseDetailView, CourseListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/<slug:slug>/", CourseDetailView.as_view(), name="course-detail"),
]
