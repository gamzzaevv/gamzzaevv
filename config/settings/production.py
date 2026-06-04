from .base import *  # noqa: F401, F403
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

# ─── Security Headers ────────────────────────────────────────────────────────

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ─── Content Security Policy ─────────────────────────────────────────────────

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://yookassa.ru", "https://widget.yookassa.ru")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_SRC = ("https://yookassa.ru",)

# ─── Sentry ──────────────────────────────────────────────────────────────────

sentry_sdk.init(
    dsn=env("SENTRY_DSN", default=""),  # noqa: F405
    integrations=[DjangoIntegration(), CeleryIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment="production",
)

# ─── S3 Storage (Yandex Object Storage) ──────────────────────────────────────

if env.bool("USE_S3", default=False):  # noqa: F405
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")  # noqa: F405
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")  # noqa: F405
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")  # noqa: F405
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")  # noqa: F405
    AWS_S3_REGION_NAME = "ru-central1"
    AWS_DEFAULT_ACL = "private"
    AWS_S3_FILE_OVERWRITE = False
