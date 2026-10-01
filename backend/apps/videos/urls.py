from django.urls import path

from .views import (
    UploadAbortView,
    UploadCompleteView,
    UploadPartsView,
    UploadStartView,
    VideoStatusView,
)

urlpatterns = [
    path("admin/videos/", UploadStartView.as_view(), name="video-upload-start"),
    path("admin/videos/<int:pk>/", VideoStatusView.as_view(), name="video-status"),
    path("admin/videos/<int:pk>/parts/", UploadPartsView.as_view(), name="video-upload-parts"),
    path(
        "admin/videos/<int:pk>/complete/",
        UploadCompleteView.as_view(),
        name="video-upload-complete",
    ),
    path("admin/videos/<int:pk>/abort/", UploadAbortView.as_view(), name="video-upload-abort"),
]
