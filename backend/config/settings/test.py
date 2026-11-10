from .base import *

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "KEY_FUNCTION": "django_tenants.cache.make_key",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
STORAGES["default"] = {"BACKEND": "django.core.files.storage.InMemoryStorage"}
STORAGES["public"] = {"BACKEND": "django.core.files.storage.InMemoryStorage"}
DATABASES["default"]["OPTIONS"].pop("pool", None)
CELERY_TASK_ALWAYS_EAGER = True
LOGGING = {
    **LOGGING,
    "handlers": {
        **LOGGING["handlers"],
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
}
# Testlar tarmoqqa chiqmasin: .env dagi haqiqiy bot tokeni ishlatilmaydi (CI dagi kabi bo'sh).
# Botni sinaydigan testlar qiymatni `settings` fixture bilan o'zi beradi.
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_BOT_USERNAME = ""
TELEGRAM_LEADS_CHAT_ID = ""
TELEGRAM_ALERTS_CHAT_ID = ""
TELEGRAM_REPORTS_CHAT_ID = ""
TELEGRAM_WEBHOOK_SECRET = ""
CLICK_SERVICE_ID = ""
CLICK_MERCHANT_ID = ""
CLICK_MERCHANT_USER_ID = ""
CLICK_SECRET_KEY = ""
CLICK_MERCHANT_TIN = ""
ESKIZ_EMAIL = ""
ESKIZ_PASSWORD = ""
# Testlar birinchi markaz nomidan ishlaydi (backend/conftest.py), `second_center` — boshqa markaz.
FIRST_CENTER_SCHEMA = "test_center"
SITE_SCHEME = "http"
SITE_PORT = ""
PLATFORM_NAME = "Test platforma"
FIRST_CENTER_NAME = "Test markaz"
SIGNUP_OPEN = True
PLATFORM_DOMAIN = "platform.testserver"
CENTERS_BASE_DOMAIN = "testserver"
# Disk va xotira — test mashinasiniki; resurs testlari qiymatni o'zi yoqadi.
RESOURCE_CHECKS = False
