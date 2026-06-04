from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.db"

CELERY_TASK_ALWAYS_EAGER = True

AXES_ENABLED = False
