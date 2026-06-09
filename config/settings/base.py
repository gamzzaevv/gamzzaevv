"""
Base settings shared across all environments.
"""
from pathlib import Path

import environ
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    USE_S3=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

SITE_URL = env("SITE_URL", default="http://localhost:8000")
SITE_NAME = env("SITE_NAME", default="MMA Start")

# ─── Application definition ──────────────────────────────────────────────────

DJANGO_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_filters",
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "celery",
    "django_celery_beat",
    "django_celery_results",
    "import_export",
    "storages",
]

LOCAL_APPS = [
    "apps.core",
    "apps.events",
    "apps.orders",
    "apps.payments",
    "apps.notifications",
    "apps.checkin",
    "apps.documents",
    "apps.accounts",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ─── Database ────────────────────────────────────────────────────────────────

DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")
}
DATABASES["default"]["CONN_MAX_AGE"] = 600

# ─── Cache & Session ─────────────────────────────────────────────────────────

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400 * 7  # 7 days

# ─── Auth ────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

# ─── Internationalization ────────────────────────────────────────────────────

LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", "Русский"),
    ("en", "English"),
]
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# ─── Static & Media ─────────────────────────────────────────────────────────

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── Email ───────────────────────────────────────────────────────────────────

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
ADMIN_EMAIL = env("ADMIN_EMAIL", default="admin@example.com")

# ─── Celery ──────────────────────────────────────────────────────────────────

CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240

# ─── YooKassa ────────────────────────────────────────────────────────────────

YOOKASSA_SHOP_ID = env("YOOKASSA_SHOP_ID", default="")
YOOKASSA_SECRET_KEY = env("YOOKASSA_SECRET_KEY", default="")
YOOKASSA_WEBHOOK_SECRET = env("YOOKASSA_WEBHOOK_SECRET", default="")
YOOKASSA_RETURN_URL = env("SITE_URL", default="http://localhost:8000") + "/orders/success/"

# ─── DRF ────────────────────────────────────────────────────────────────────

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "100/minute",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ─── Axes (Brute Force Protection) ───────────────────────────────────────────

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hour
AXES_LOCKOUT_TEMPLATE = "accounts/lockout.html"
AXES_RESET_ON_SUCCESS = True

# ─── Django Allauth ──────────────────────────────────────────────────────────

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
MFA_ADAPTER = "allauth.mfa.adapter.DefaultMFAAdapter"
MFA_TOTP_PERIOD = 30

# ─── Sites ───────────────────────────────────────────────────────────────────

SITE_ID = 1

# ─── Django Unfold Admin ─────────────────────────────────────────────────────

UNFOLD = {
    "SITE_TITLE": "Управление билетами",
    "SITE_HEADER": "Билеты MMA Start",
    "SITE_SYMBOL": "sports_mma",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SIDEBAR": {
        "show_search": True,
        "navigation": [
            {
                "title": "Продажи",
                "separator": True,
                "items": [
                    {
                        "title": "Заказы",
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:orders_order_changelist"),
                    },
                    {
                        "title": "Билеты",
                        "icon": "confirmation_number",
                        "link": reverse_lazy("admin:orders_ticket_changelist"),
                    },
                    {
                        "title": "Покупатели",
                        "icon": "group",
                        "link": reverse_lazy("admin:orders_customer_changelist"),
                    },
                ],
            },
            {
                "title": "Мероприятие",
                "separator": True,
                "items": [
                    {
                        "title": "Дни боёв",
                        "icon": "stadium",
                        "link": reverse_lazy("admin:events_event_changelist"),
                    },
                    {
                        "title": "Промокоды",
                        "icon": "local_offer",
                        "link": reverse_lazy("admin:events_promocode_changelist"),
                    },
                ],
            },
            {
                "title": "Контроль на входе",
                "separator": True,
                "items": [
                    {
                        "title": "Журнал проверок",
                        "icon": "qr_code_scanner",
                        "link": reverse_lazy("admin:checkin_checkinlog_changelist"),
                    },
                ],
            },
            {
                "title": "Контент",
                "separator": True,
                "items": [
                    {
                        "title": "Документы (оферта и пр.)",
                        "icon": "description",
                        "link": reverse_lazy("admin:documents_documentpage_changelist"),
                    },
                ],
            },
            {
                "title": "Служебное",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Платежи",
                        "icon": "payments",
                        "link": reverse_lazy("admin:payments_payment_changelist"),
                    },
                    {
                        "title": "Письма (email)",
                        "icon": "mail",
                        "link": reverse_lazy("admin:notifications_emaillog_changelist"),
                    },
                    {
                        "title": "Сотрудники",
                        "icon": "manage_accounts",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                    },
                ],
            },
        ],
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
