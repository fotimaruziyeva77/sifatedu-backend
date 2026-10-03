"""Umumiy sozlamalar. Muhitga xos qiymatlar environment o'zgaruvchilaridan olinadi."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import environ
from celery.schedules import crontab
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _can(permission: str) -> Callable[[Any], bool]:
    """Admin menyusi: bo'lim faqat ruxsati borlarga ko'rinadi (rollar — apps/users/roles.py)."""
    return lambda request: bool(request.user.has_perm(permission))


env = environ.Env()

# --- Asosiy ---
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
APP_URL = env("APP_URL", default="http://localhost")
API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=False)

INSTALLED_APPS = [
    # modeltranslation va unfold django.contrib.admin'dan oldin turishi shart
    "modeltranslation",
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "auditlog",
    "apps.core",
    "apps.users",
    "apps.catalog",
    "apps.content",
    "apps.leads",
    "apps.notifications",
    "apps.videos",
    "apps.learning",
    "apps.payments",
    "apps.assistant",
    "apps.homework",
    "apps.quizzes",
    "apps.live",
    "apps.exams",
    "apps.certificates",
    "apps.rewards",
    "apps.shop",
    "apps.placement",
    "apps.dailytest",
    "apps.bot",
    "apps.stats",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Ma'lumotlar bazasi ---
# ASGI'da doimiy ulanishlar o'rniga psycopg pool ishlatiladi.
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"].setdefault("OPTIONS", {})["pool"] = {
    "min_size": env.int("DB_POOL_MIN_SIZE", default=1),
    "max_size": env.int("DB_POOL_MAX_SIZE", default=10),
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Kesh va sessiyalar ---
REDIS_URL = env("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "sifat",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# Frontend CSRF tokenni cookie'dan o'qib, X-CSRFToken header'ida yuboradi.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"

# --- Autentifikatsiya ---
AUTH_USER_MODEL = "users.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Til va vaqt ---
LANGUAGE_CODE = "uz"
LANGUAGES = [
    ("uz", "O'zbekcha"),
    ("ru", "Русский"),
    ("en", "English"),
]
MODELTRANSLATION_DEFAULT_LANGUAGE = "uz"
MODELTRANSLATION_FALLBACK_LANGUAGES = ("uz",)
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

# --- Static va fayllar ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

S3_ENDPOINT = env("S3_ENDPOINT", default=None)
S3_PUBLIC_ENDPOINT = env("S3_PUBLIC_ENDPOINT", default=S3_ENDPOINT or "")
S3_BUCKET_PRIVATE = env("S3_BUCKET_PRIVATE", default="sifat-private")
S3_BUCKET_PUBLIC = env("S3_BUCKET_PUBLIC", default="sifat-public")
S3_PUBLIC_BASE_URL = env(
    "S3_PUBLIC_BASE_URL",
    default=f"{S3_PUBLIC_ENDPOINT.rstrip('/')}/{S3_BUCKET_PUBLIC}",
)
_public_url = urlsplit(S3_PUBLIC_BASE_URL)

AWS_S3_ENDPOINT_URL = S3_ENDPOINT
AWS_S3_REGION_NAME = env("S3_REGION", default="us-east-1")
AWS_ACCESS_KEY_ID = env("S3_ACCESS_KEY", default="")
AWS_SECRET_ACCESS_KEY = env("S3_SECRET_KEY", default="")
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None

STORAGES = {
    # Yopiq fayllar (videolar, materiallar): faqat imzolangan URL orqali.
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {"bucket_name": S3_BUCKET_PRIVATE, "querystring_auth": True},
    },
    # Ochiq fayllar (kurs muqovasi, ustoz rasmi, avatar).
    "public": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": S3_BUCKET_PUBLIC,
            "querystring_auth": False,
            "custom_domain": f"{_public_url.netloc}{_public_url.path}",
            "url_protocol": f"{_public_url.scheme}:",
        },
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --- Video ---
# Brauzer faylni to'g'ridan-to'g'ri storage'ga yuklaydi: backend faqat imzolangan URL beradi.
MAX_VIDEO_SIZE_MB = env.int("MAX_VIDEO_SIZE_MB", default=2048)
VIDEO_PART_SIZE_MB = env.int("VIDEO_PART_SIZE_MB", default=16)
# HLS segmentlari va kalitiga berilgan imzoning muddati.
HLS_SIGNED_URL_TTL_SEC = env.int("HLS_SIGNED_URL_TTL_SEC", default=7200)
# Segment shifrlash kaliti shu sir bilan shifrlangan holda bazada saqlanadi.
VIDEO_KEY_SECRET = env("VIDEO_KEY_SECRET", default=SECRET_KEY)
FFMPEG_BIN = env("FFMPEG_BIN", default="ffmpeg")
FFPROBE_BIN = env("FFPROBE_BIN", default="ffprobe")
# Brauzer S3'ga o'zi murojaat qiladi, shuning uchun bucket'da CORS kerak.
S3_CORS_ORIGINS = env.list("S3_CORS_ORIGINS", default=[APP_URL])

# --- DRF va OpenAPI ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "300/min",
        "leads": "10/hour",
        # Auth: IP bo'yicha. Raqam bo'yicha limitlar apps/users/otp.py va services.py'da.
        "otp": "20/hour",
        "login": "60/hour",
        "auth_verify": "30/hour",
        "orders": "20/hour",
        # AI chatga yozish (IP bo'yicha); suhbat ichidagi limit — admin'da.
        "assistant": "60/hour",
        # Telegram'ni ulash havolasi (foydalanuvchi bo'yicha).
        "telegram_link": "10/hour",
        # Uy vazifasi javobi (fayllar bilan).
        "homework": "30/hour",
        # Test: har bir javob alohida so'rov.
        "quiz": "600/hour",
    },
    # nginx orqasida: haqiqiy IP X-Forwarded-For'dan olinadi.
    "NUM_PROXIES": 1,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sifat Edu API",
    "DESCRIPTION": "Sifat Edu platformasi REST API'si. Autentifikatsiya: session cookie + CSRF.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    # Bir xil nomli, lekin har xil qiymatli tanlovlar: frontend tiplari barqaror nomlansin.
    "ENUM_NAME_OVERRIDES": {
        "LanguageEnum": LANGUAGES,
        "CourseAudienceEnum": "apps.catalog.models.Course.Audience",
        "UserAudienceEnum": "apps.users.models.User.Audience",
        "CourseIconEnum": "apps.catalog.models.Course.Icon",
        "AdvantageIconEnum": "apps.content.models.Advantage.Icon",
        "CourseFormatEnum": "apps.catalog.models.Course.Format",
        "StudyFormatEnum": "apps.payments.models.Order.Format",
        "StudyGroupStatusEnum": "apps.learning.models.StudyGroup.Status",
        "HomeworkStatusEnum": "apps.homework.serializers.HOMEWORK_STATUSES",
        "SubmissionStatusEnum": "apps.homework.models.Submission.Status",
        "CodeLanguageEnum": "apps.homework.serializers.CODE_LANGUAGES",
        "AttendanceStatusEnum": "apps.live.models.Attendance.Status",
        "DailyTaskKindEnum": "apps.rewards.models.DailyTask.Kind",
        "RewardReasonEnum": "apps.rewards.models.Entry.Reason",
        "RatingPeriodEnum": "apps.rewards.serializers.PERIODS",
        "RatingScopeEnum": "apps.rewards.serializers.SCOPES",
        "DiscountReasonEnum": "apps.rewards.serializers.DISCOUNTS",
        "CouponKindEnum": "apps.rewards.models.Coupon.Kind",
        "DailyTestStatusEnum": "apps.dailytest.models.DailyTest.Status",
        "DailyStudentStatusEnum": "apps.dailytest.serializers.STUDENT_STATUSES",
        "DailyDayStatusEnum": "apps.dailytest.serializers.DAY_STATUSES",
    },
}

# --- Celery ---
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "apps.videos.tasks.*": {"queue": "video"},
    # AI javobi 5–20 soniya: alohida navbat, SMS kodlari va bot tugmalari kutib qolmasin.
    "apps.assistant.tasks.answer": {"queue": "ai"},
    "apps.assistant.tasks.telegram_answer": {"queue": "ai"},
    # Ommaviy xabarlar alohida navbatda: SMS kodlari ularni kutib qolmaydi.
    "apps.notifications.tasks.deliver": {"queue": "bulk"},
    "apps.bot.tasks.deliver_news": {"queue": "bulk"},
}
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# Standart qiymat CPU soniga teng bo'ladi; xotirani tejash uchun aniq belgilanadi.
CELERY_WORKER_CONCURRENCY = env.int("CELERY_WORKER_CONCURRENCY", default=2)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULE: dict[str, dict[str, object]] = {
    # To'lanmagan buyurtma 30 daqiqada yopiladi; tekshiruv har 5 daqiqada.
    "expire-orders": {
        "task": "apps.payments.tasks.expire_orders",
        "schedule": 300.0,
    },
    # AI suhbatlari 90 kundan keyin anonimlashtiriladi (TZ 4.9).
    "anonymize-conversations": {
        "task": "apps.assistant.tasks.anonymize_old_conversations",
        "schedule": 24 * 60 * 60.0,
    },
    # Tunda "Yuborish" bosilgan aksiyalar ertalab 09:00 da ketadi.
    "send-scheduled-broadcasts": {
        "task": "apps.notifications.tasks.send_scheduled_broadcasts",
        "schedule": 300.0,
    },
    # Offlayn kurs: to'lov muddati tugashidan 3 kun oldin va tugagan kuni.
    "remind-expiring": {
        "task": "apps.notifications.tasks.remind_expiring",
        "schedule": crontab(hour=10, minute=0),
    },
    # Kursni boshlab, 3 va 7 kundan beri o'qimaganlarga eslatma.
    "remind-inactive": {
        "task": "apps.notifications.tasks.remind_inactive",
        "schedule": crontab(hour=10, minute=5),
    },
    # Jonli darslar: haftalik jadvaldan 14 kun oldinga (har kecha) va eslatmalar (har 5 daqiqa).
    "generate-live-lessons": {
        "task": "apps.live.tasks.generate_live_lessons",
        "schedule": crontab(hour=1, minute=30),
    },
    "remind-live-lessons": {
        "task": "apps.live.tasks.remind_live_lessons",
        "schedule": 300.0,
    },
    # Oylik imtihon: 20-kuni qoralama, har 5 daqiqada ochilish xabari, vaqti tugagan testlar va
    # yakuniy natijalar; har kecha sertifikat shartlari.
    "exam-drafts": {
        "task": "apps.exams.tasks.create_exam_drafts",
        "schedule": crontab(day_of_month="20", hour=9, minute=0),
    },
    "exam-tick": {
        "task": "apps.exams.tasks.exam_tick",
        "schedule": 300.0,
    },
    "certificates-sweep": {
        "task": "apps.certificates.tasks.sweep_certificates",
        "schedule": crontab(hour=3, minute=15),
    },
    # Kunlik topshiriqlar 09:00 da, kechagi bajarilmaganlarga shtraf 00:10 da; dushanba 10:00 —
    # haftalik g'oliblar (admin'da yoqilgan bo'lsa).
    "daily-tasks": {
        "task": "apps.rewards.tasks.daily_tasks",
        "schedule": crontab(hour=9, minute=0),
    },
    "daily-close": {
        "task": "apps.rewards.tasks.close_day",
        "schedule": crontab(hour=0, minute=10),
    },
    "weekly-winners": {
        "task": "apps.rewards.tasks.weekly_winners",
        "schedule": crontab(day_of_week=1, hour=10, minute=0),
    },
    # Guruhlarga kunlik test: 07:00 da ochiladi (07:30 da qayta — deploy paytida o'tib ketmasin),
    # 20:00 da ishlamaganlarga eslatma, yopilishi — 23:00 dan keyin har 15 daqiqada tekshiriladi.
    "daily-test-open": {
        "task": "apps.dailytest.tasks.open_day",
        "schedule": crontab(hour=7, minute="0,30"),
    },
    "daily-test-remind": {
        "task": "apps.dailytest.tasks.remind",
        "schedule": crontab(hour=20, minute=0),
    },
    "daily-test-close": {
        "task": "apps.dailytest.tasks.close_day",
        "schedule": crontab(minute="*/15"),
    },
    # Daraja testi: vaqti tugagan testlar (har 5 daqiqa) — natija, kupon va ariza; kupon
    # eslatmalari — 24 soatdan keyin va muddat tugashiga 12 soat qolganda.
    "placement-close-expired": {
        "task": "apps.placement.tasks.close_expired",
        "schedule": 300.0,
    },
    "placement-coupon-reminders": {
        "task": "apps.placement.tasks.coupon_reminders",
        "schedule": crontab(minute=20),
    },
    # Server diski va xotirasi: chegaradan oshsa — jamoaga Telegram ogohlantirish.
    "check-server-resources": {
        "task": "apps.core.tasks.check_server_resources",
        "schedule": crontab(minute=7),
    },
    # Kunlik hisobot direktor va adminlarga (Telegram).
    "daily-report": {
        "task": "apps.stats.tasks.send_daily_report",
        "schedule": crontab(hour=env.int("DAILY_REPORT_HOUR", default=21), minute=0),
    },
}

# --- Server resurslari (soatlik tekshiruv: Telegram ogohlantirish va admin "Muammolar") ---
RESOURCE_CHECKS = env.bool("RESOURCE_CHECKS", default=True)
DISK_ALERT_PERCENT = env.int("DISK_ALERT_PERCENT", default=85)
MEMORY_ALERT_FREE_PERCENT = env.int("MEMORY_ALERT_FREE_PERCENT", default=10)

# --- SMS (Eskiz.uz) ---
# DRY_RUN rejimida SMS yuborilmaydi, matn logga yoziladi (local va testlar uchun).
SMS_DRY_RUN = env.bool("SMS_DRY_RUN", default=True)
ESKIZ_EMAIL = env("ESKIZ_EMAIL", default="")
ESKIZ_PASSWORD = env("ESKIZ_PASSWORD", default="")
ESKIZ_FROM = env("ESKIZ_FROM", default="4546")
# Ommaviy xabarda SMS narxini taxminlash uchun (bitta SMS bo'lagi, so'm).
SMS_PRICE_UZS = env.int("SMS_PRICE_UZS", default=100)

# --- Ijtimoiy kirish ---
# Google Cloud Console → OAuth client ID (Web). Bo'sh bo'lsa, tugma saytda ko'rinmaydi.
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
# Telegram Login Widget: bot nomi (@siz) va leads bilan umumiy TELEGRAM_BOT_TOKEN.
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")

# --- To'lov (Click SHOP API) ---
# Kalitlar bo'lmasa, sayt to'lov tugmasini ko'rsatmaydi va buyurtma yaratilmaydi.
CLICK_SERVICE_ID = env("CLICK_SERVICE_ID", default="")
CLICK_MERCHANT_ID = env("CLICK_MERCHANT_ID", default="")
CLICK_MERCHANT_USER_ID = env("CLICK_MERCHANT_USER_ID", default="")
CLICK_SECRET_KEY = env("CLICK_SECRET_KEY", default="")
# Fiskal chek uchun: soliq to'lovchi raqami (STIR).
CLICK_MERCHANT_TIN = env("CLICK_MERCHANT_TIN", default="")
# DRY_RUN da chek yuborilmaydi, ma'lumot logga yoziladi (SMS'dagi kabi).
FISCAL_DRY_RUN = env.bool("FISCAL_DRY_RUN", default=True)

# --- Telegram ---
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_LEADS_CHAT_ID = env("TELEGRAM_LEADS_CHAT_ID", default="")
TELEGRAM_ALERTS_CHAT_ID = env("TELEGRAM_ALERTS_CHAT_ID", default="")
# Kunlik hisobot guruhi (ixtiyoriy). Direktor va adminlarga (Telegram ulangan) baribir boradi.
TELEGRAM_REPORTS_CHAT_ID = env("TELEGRAM_REPORTS_CHAT_ID", default="")
# Bot webhook'i: Telegram har so'rovda shu kalitni header'da yuboradi (`telegram_webhook set`).
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")

# --- AI maslahatchi (Google Gemini API) ---
# Kalit: aistudio.google.com → API keys (pullik tarif: bepulida yozishmalar Google mahsulotlarini
# yaxshilashga ishlatilishi mumkin). Kalit bo'lmasa va DRY_RUN o'chiq bo'lsa, saytda chat yo'q.
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
# Standart — Gemini 3.8 Flash (barqaror, tez). Model va narx birga o'zgartiriladi.
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-3.8-flash")
# Fikrlash chuqurligi: minimal | low | medium | high. Chat uchun past — tezroq va arzonroq.
GEMINI_THINKING_LEVEL = env("GEMINI_THINKING_LEVEL", default="low")
# Narxlar, $ / 1M token: ai.google.dev/gemini-api/docs/pricing. 3.8 Flash: 1.50 / 7.50 (2026 yil
# oxirigacha aksiya — 0.75 / 3.75; budjet zaxira bilan hisoblanadi).
GEMINI_PRICE_INPUT = env.float("GEMINI_PRICE_INPUT", default=1.5)
GEMINI_PRICE_OUTPUT = env.float("GEMINI_PRICE_OUTPUT", default=7.5)
# Javob chegarasi (fikrlash tokenlari ham kiradi). Odatdagi javob bundan ancha qisqa.
ASSISTANT_MAX_TOKENS = env.int("ASSISTANT_MAX_TOKENS", default=16000)
# DRY_RUN: Gemini chaqirilmaydi (kalit bo'lsa ham) — oddiy rejim "test rejimi" belgisi bilan
# (E2E va pulsiz sinov uchun). `assistant_eval` bunga qaramaydi.
ASSISTANT_DRY_RUN = env.bool("ASSISTANT_DRY_RUN", default=False)
ASSISTANT_RETENTION_DAYS = env.int("ASSISTANT_RETENTION_DAYS", default=90)

# --- Xavfsizlik ---
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# --- Audit log ---
# Admin'dagi o'zgarishlar: kim, qachon, qaysi maydon (eski → yangi).
AUDITLOG_INCLUDE_TRACKING_MODELS = (
    "catalog.Category",
    "catalog.Instructor",
    {"model": "catalog.Course", "m2m_fields": ["instructors"]},
    "catalog.Module",
    "catalog.Lesson",
    "learning.Enrollment",
    "payments.Order",
    "payments.Refund",
    "assistant.AssistantSettings",
    "content",
    "leads",
    {
        "model": "users.User",
        "exclude_fields": ["password", "last_login"],
        "m2m_fields": ["groups"],
    },
    {"model": "auth.Group", "m2m_fields": ["permissions"]},
)

# --- Admin (Unfold) ---
UNFOLD = {
    "SITE_TITLE": "Sifat Edu",
    "SITE_HEADER": "Sifat Edu",
    "SITE_SUBHEADER": "Boshqaruv paneli",
    "SITE_URL": "/",
    "SITE_SYMBOL": "school",
    "SITE_LOGO": {
        "light": lambda request: static("brand/logo-light.svg"),
        "dark": lambda request: static("brand/logo-dark.svg"),
    },
    "SITE_FAVICONS": [
        {"rel": "icon", "type": "image/svg+xml", "href": lambda request: static("brand/icon.svg")},
    ],
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "apps.core.admin_config.environment_callback",
    # Bosh sahifa: kunlik statistika va muammolar (ruxsati borlarga).
    "DASHBOARD_CALLBACK": "apps.stats.dashboard.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Sotuv",
                "items": [
                    {
                        "title": "Arizalar",
                        "icon": "contact_phone",
                        "link": reverse_lazy("admin:leads_lead_changelist"),
                        "permission": _can("leads.view_lead"),
                        "badge": "apps.core.admin_config.new_leads_badge",
                    },
                    {
                        "title": "Daraja testlari",
                        "icon": "quiz",
                        "link": reverse_lazy("admin:placement_placementtest_changelist"),
                        "permission": _can("placement.view_placementtest"),
                    },
                    {
                        "title": "Daraja testi natijalari",
                        "icon": "fact_check",
                        "link": reverse_lazy("admin:placement_placementattempt_changelist"),
                        "permission": _can("placement.view_placementattempt"),
                    },
                ],
            },
            {
                "title": "AI yordamchi",
                "items": [
                    {
                        "title": "Suhbatlar",
                        "icon": "forum",
                        "link": reverse_lazy("admin:assistant_conversation_changelist"),
                        "permission": _can("assistant.view_conversation"),
                        "badge": "apps.core.admin_config.manager_needed_badge",
                    },
                    {
                        "title": "AI sozlamalari",
                        "icon": "smart_toy",
                        "link": reverse_lazy("admin:assistant_assistantsettings_changelist"),
                        "permission": _can("assistant.view_assistantsettings"),
                    },
                ],
            },
            {
                "title": "Telegram bot",
                "items": [
                    {
                        "title": "Bot foydalanuvchilari",
                        "icon": "chat",
                        "link": reverse_lazy("admin:bot_botchat_changelist"),
                        "permission": _can("bot.view_botchat"),
                    },
                    {
                        "title": "Majburiy kanallar",
                        "icon": "podcasts",
                        "link": reverse_lazy("admin:bot_requiredchannel_changelist"),
                        "permission": _can("bot.view_requiredchannel"),
                    },
                ],
            },
            {
                "title": "Katalog",
                "items": [
                    {
                        "title": "Kurslar",
                        "icon": "school",
                        "link": reverse_lazy("admin:catalog_course_changelist"),
                        "permission": _can("catalog.view_course"),
                    },
                    {
                        "title": "Modullar",
                        "icon": "view_module",
                        "link": reverse_lazy("admin:catalog_module_changelist"),
                        "permission": _can("catalog.view_module"),
                    },
                    {
                        "title": "Darslar",
                        "icon": "play_lesson",
                        "link": reverse_lazy("admin:catalog_lesson_changelist"),
                        "permission": _can("catalog.view_lesson"),
                    },
                    {
                        "title": "Kategoriyalar",
                        "icon": "category",
                        "link": reverse_lazy("admin:catalog_category_changelist"),
                        "permission": _can("catalog.view_category"),
                    },
                    {
                        "title": "Ustozlar",
                        "icon": "person_book",
                        "link": reverse_lazy("admin:catalog_instructor_changelist"),
                        "permission": _can("catalog.view_instructor"),
                    },
                ],
            },
            {
                "title": "To'lovlar",
                "items": [
                    {
                        "title": "Buyurtmalar",
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:payments_order_changelist"),
                        "permission": _can("payments.view_order"),
                    },
                    {
                        "title": "Tranzaksiyalar",
                        "icon": "payments",
                        "link": reverse_lazy("admin:payments_paymenttransaction_changelist"),
                        "permission": _can("payments.view_paymenttransaction"),
                    },
                    {
                        "title": "Pul qaytarish",
                        "icon": "currency_exchange",
                        "link": reverse_lazy("admin:payments_refund_changelist"),
                        "permission": _can("payments.view_refund"),
                    },
                    {
                        "title": "To'lov loglari",
                        "icon": "terminal",
                        "link": reverse_lazy("admin:payments_paymentlog_changelist"),
                        "permission": _can("payments.view_paymentlog"),
                    },
                ],
            },
            {
                "title": "O'qish",
                "items": [
                    {
                        "title": "Kursga yozilishlar",
                        "icon": "how_to_reg",
                        "link": reverse_lazy("admin:learning_enrollment_changelist"),
                        "permission": _can("learning.view_enrollment"),
                    },
                    {
                        "title": "Guruhlar",
                        "icon": "groups",
                        "link": reverse_lazy("admin:learning_studygroup_changelist"),
                        "permission": _can("learning.view_studygroup"),
                    },
                    {
                        "title": "Jonli darslar",
                        "icon": "video_call",
                        "link": reverse_lazy("admin:live_livelesson_changelist"),
                        "permission": _can("live.view_livelesson"),
                    },
                    {
                        "title": "Testlar",
                        "icon": "quiz",
                        "link": reverse_lazy("admin:quizzes_quiz_changelist"),
                        "permission": _can("quizzes.view_quiz"),
                    },
                    {
                        "title": "Oylik imtihonlar",
                        "icon": "fact_check",
                        "link": reverse_lazy("admin:exams_exam_changelist"),
                        "permission": _can("exams.view_exam"),
                    },
                    {
                        "title": "Kunlik testlar",
                        "icon": "today",
                        "link": reverse_lazy("admin:dailytest_dailytest_changelist"),
                        "permission": _can("dailytest.view_dailytest"),
                    },
                    {
                        "title": "Sertifikatlar",
                        "icon": "workspace_premium",
                        "link": reverse_lazy("admin:certificates_certificate_changelist"),
                        "permission": _can("certificates.view_certificate"),
                    },
                    {
                        "title": "Uy vazifalari",
                        "icon": "assignment",
                        "link": reverse_lazy("admin:homework_submission_changelist"),
                        "permission": _can("homework.view_submission"),
                    },
                    {
                        "title": "Videolar",
                        "icon": "movie",
                        "link": reverse_lazy("admin:videos_videoasset_changelist"),
                        "permission": _can("videos.view_videoasset"),
                    },
                    {
                        "title": "Dars progressi",
                        "icon": "trending_up",
                        "link": reverse_lazy("admin:learning_lessonprogress_changelist"),
                        "permission": _can("learning.view_lessonprogress"),
                    },
                ],
            },
            {
                "title": "XP va coin",
                "items": [
                    {
                        "title": "Sozlamalar",
                        "icon": "tune",
                        "link": reverse_lazy("admin:rewards_gamesettings_changelist"),
                        "permission": _can("rewards.view_gamesettings"),
                    },
                    {
                        "title": "Tarix",
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:rewards_entry_changelist"),
                        "permission": _can("rewards.view_entry"),
                    },
                    {
                        "title": "Hamyonlar",
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:rewards_wallet_changelist"),
                        "permission": _can("rewards.view_wallet"),
                    },
                    {
                        "title": "Kunlik topshiriqlar",
                        "icon": "task_alt",
                        "link": reverse_lazy("admin:rewards_dailytask_changelist"),
                        "permission": _can("rewards.view_dailytask"),
                    },
                    {
                        "title": "Kuponlar",
                        "icon": "confirmation_number",
                        "link": reverse_lazy("admin:rewards_coupon_changelist"),
                        "permission": _can("rewards.view_coupon"),
                    },
                    {
                        "title": "Do'kon: sovg'alar",
                        "icon": "redeem",
                        "link": reverse_lazy("admin:shop_product_changelist"),
                        "permission": _can("shop.view_product"),
                    },
                    {
                        "title": "Do'kon: buyurtmalar",
                        "icon": "shopping_bag",
                        "link": reverse_lazy("admin:shop_purchase_changelist"),
                        "permission": _can("shop.view_purchase"),
                    },
                ],
            },
            {
                "title": "Sayt kontenti",
                "items": [
                    {
                        "title": "Sozlamalar va hero",
                        "icon": "tune",
                        "link": reverse_lazy("admin:content_sitesettings_changelist"),
                        "permission": _can("content.view_sitesettings"),
                    },
                    {
                        "title": "Xavotirlar",
                        "icon": "psychology_alt",
                        "link": reverse_lazy("admin:content_concern_changelist"),
                        "permission": _can("content.view_concern"),
                    },
                    {
                        "title": "Afzalliklar",
                        "icon": "stars",
                        "link": reverse_lazy("admin:content_advantage_changelist"),
                        "permission": _can("content.view_advantage"),
                    },
                    {
                        "title": "Qanday ishlaydi",
                        "icon": "route",
                        "link": reverse_lazy("admin:content_howstep_changelist"),
                        "permission": _can("content.view_howstep"),
                    },
                    {
                        "title": "FAQ",
                        "icon": "quiz",
                        "link": reverse_lazy("admin:content_faqitem_changelist"),
                        "permission": _can("content.view_faqitem"),
                    },
                    {
                        "title": "Fikrlar",
                        "icon": "reviews",
                        "link": reverse_lazy("admin:content_testimonial_changelist"),
                        "permission": _can("content.view_testimonial"),
                    },
                    {
                        "title": "Huquqiy sahifalar",
                        "icon": "gavel",
                        "link": reverse_lazy("admin:content_legalpage_changelist"),
                        "permission": _can("content.view_legalpage"),
                    },
                ],
            },
            {
                "title": "Xabarnomalar",
                "items": [
                    {
                        "title": "Xabar yuborish",
                        "icon": "campaign",
                        "link": reverse_lazy("admin:notifications_broadcast_changelist"),
                        "permission": _can("notifications.view_broadcast"),
                    },
                    {
                        "title": "Yuborilgan xabarlar",
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                        "permission": _can("notifications.view_notification"),
                    },
                ],
            },
            {
                "title": "Foydalanuvchilar",
                "items": [
                    {
                        "title": "Foydalanuvchilar",
                        "icon": "group",
                        "link": reverse_lazy("admin:users_user_changelist"),
                        "permission": _can("users.view_user"),
                    },
                    {
                        "title": "SMS kodlar",
                        "icon": "sms",
                        "link": reverse_lazy("admin:users_onetimecode_changelist"),
                        "permission": _can("users.view_onetimecode"),
                    },
                    {
                        "title": "Rollar",
                        "icon": "badge",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": _can("auth.view_group"),
                    },
                    {
                        "title": "Audit log",
                        "icon": "history",
                        "link": reverse_lazy("admin:auditlog_logentry_changelist"),
                        "permission": _can("auditlog.view_logentry"),
                    },
                ],
            },
        ],
    },
    "COLORS": {
        # Neytral kulrang: logodagi qora fonga mos.
        "base": {
            "50": "oklch(98.5% 0 0)",
            "100": "oklch(97% 0 0)",
            "200": "oklch(92.2% 0 0)",
            "300": "oklch(87% 0 0)",
            "400": "oklch(70.8% 0 0)",
            "500": "oklch(55.6% 0 0)",
            "600": "oklch(43.9% 0 0)",
            "700": "oklch(37.1% 0 0)",
            "800": "oklch(26.9% 0 0)",
            "900": "oklch(20.5% 0 0)",
            "950": "oklch(14.5% 0 0)",
        },
        # Brend qizili (#E31E24 ≈ 600).
        "primary": {
            "50": "oklch(97.1% .013 17.38)",
            "100": "oklch(93.6% .032 17.717)",
            "200": "oklch(88.5% .062 18.334)",
            "300": "oklch(80.8% .114 19.571)",
            "400": "oklch(70.4% .191 22.216)",
            "500": "oklch(63.7% .237 25.331)",
            "600": "oklch(57.7% .245 27.325)",
            "700": "oklch(50.5% .213 27.518)",
            "800": "oklch(44.4% .177 26.899)",
            "900": "oklch(39.6% .141 25.723)",
            "950": "oklch(25.8% .092 26.042)",
        },
    },
}

# --- Loglar ---
LOG_FORMAT = env("LOG_FORMAT", default="json")
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "apps.core.logging.JsonFormatter"},
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": LOG_FORMAT},
        # Kunlik statistika uchun: xatolar kun va bo'lim bo'yicha sanaladi (apps/stats/errors.py).
        "error_counter": {"()": "apps.stats.errors.ErrorCounter"},
    },
    "root": {"handlers": ["console", "error_counter"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING", "propagate": True}},
}
