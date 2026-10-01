from apps.core.sentry import init_sentry

from .base import *

DEBUG = False

# --- HTTPS ---
# TLS'ni nginx tugatadi va HTTP → HTTPS redirectni ham o'zi qiladi. Django redirect qilmaydi:
# Next.js server backend'ga ichki tarmoqda oddiy HTTP bilan murojaat qiladi.
SECURE_SSL_REDIRECT = False
# W021: HSTS preload — qaytarib bo'lmaydigan qaror, shuning uchun env orqali ongli yoqiladi.
SILENCED_SYSTEM_CHECKS = ["security.W008", "security.W021"]
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# --- Monitoring ---
init_sentry(
    dsn=env("SENTRY_DSN", default=""),
    environment=env("SENTRY_ENVIRONMENT", default="production"),
    traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
)
