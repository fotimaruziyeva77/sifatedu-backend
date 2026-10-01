from .base import *

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
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
