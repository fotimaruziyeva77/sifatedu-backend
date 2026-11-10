from django.urls import path

from .platform_api import (
    AddressView,
    PlansView,
    SignupCreateView,
    SignupResendView,
    SignupStatusView,
    SignupVerifyView,
)

urlpatterns = [
    path("plans/", PlansView.as_view(), name="platform-plans"),
    path("address/", AddressView.as_view(), name="platform-address"),
    path("signups/", SignupCreateView.as_view(), name="platform-signups"),
    path("signups/<uuid:token>/", SignupStatusView.as_view(), name="platform-signup"),
    path("signups/<uuid:token>/resend/", SignupResendView.as_view(), name="platform-resend"),
    path("signups/<uuid:token>/verify/", SignupVerifyView.as_view(), name="platform-verify"),
]
