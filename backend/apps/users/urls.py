from django.urls import path

from .views import (
    CsrfView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    MeView,
    OtpView,
    PasswordChangeView,
    PasswordResetView,
    RegisterView,
    SocialPhoneView,
    SocialProvidersView,
    TelegramLoginView,
)

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/otp/", OtpView.as_view(), name="auth-otp"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/password/reset/", PasswordResetView.as_view(), name="auth-password-reset"),
    path("auth/social/", SocialProvidersView.as_view(), name="auth-social-providers"),
    path("auth/social/google/", GoogleLoginView.as_view(), name="auth-social-google"),
    path("auth/social/telegram/", TelegramLoginView.as_view(), name="auth-social-telegram"),
    path("auth/social/phone/", SocialPhoneView.as_view(), name="auth-social-phone"),
    path("me/", MeView.as_view(), name="me"),
    path("me/password/", PasswordChangeView.as_view(), name="me-password"),
]
