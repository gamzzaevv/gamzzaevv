"""
Настройки для виртуального хостинга reg.ru.
- Без Redis: кеш на файлах, сессии в MySQL
- Без Celery-воркера: задачи выполняются синхронно в том же запросе
- PyMySQL вместо mysqlclient (не требует системных библиотек)
- SSL завершается на прокси reg.ru, Django получает HTTP
"""
import pymysql

pymysql.install_as_MySQLdb()

from .base import *  # noqa: F401, F403, E402

# ── Безопасность (SSL на стороне reg.ru, не в Django) ────────────────────────

SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_TRUSTED_ORIGINS = env.list(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    default=["https://mmastart.ru", "https://www.mmastart.ru"],
)
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ── Content Security Policy ───────────────────────────────────────────────────

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://yookassa.ru", "https://widget.yookassa.ru")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_SRC = ("https://yookassa.ru",)

# ── Сессии: в базе данных (Redis недоступен) ─────────────────────────────────

SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ── Кеш: файловый (Redis недоступен) ─────────────────────────────────────────

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": BASE_DIR / ".cache",  # noqa: F405
    }
}

# ── MySQL: без постоянных соединений на shared hosting ───────────────────────

DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405

# ── Celery: синхронный режим, воркер и брокер не нужны ───────────────────────
# Все .delay() и .apply_async() выполняются мгновенно в текущем процессе.

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "django-db"

# ── Статика ───────────────────────────────────────────────────────────────────

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# ── Sentry (опционально) ──────────────────────────────────────────────────────

import sentry_sdk  # noqa: E402
from sentry_sdk.integrations.django import DjangoIntegration  # noqa: E402

_sentry_dsn = env("SENTRY_DSN", default="")  # noqa: F405
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production",
    )
