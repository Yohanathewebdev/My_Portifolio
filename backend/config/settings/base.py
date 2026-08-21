from pathlib import Path

import environ

from apps.core.logging import configure_structlog

BASE_DIR = Path(__file__).resolve().parents[3]
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = env("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.billing",
    "apps.portfolios",
]
AUTH_USER_MODEL = "accounts.User"
PORTFOLIO_RESOLVER = "apps.portfolios.resolvers.resolve_portfolio"
ACCOUNT_RESOLVER = "apps.accounts.resolvers.resolve_accounts"
ACCOUNT_REQUEST_RESOLVER = "apps.accounts.resolvers.resolve_account"
MEMBERSHIP_ROLE_RESOLVER = "apps.accounts.resolvers.resolve_role"
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.core.middleware.CorrelationIdMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://portfolio:portfolio@localhost:5432/portfolio",
    )
}
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
STORAGE_ENDPOINT = env("STORAGE_ENDPOINT", default="http://localhost:9000")
STORAGE_BUCKET = env("STORAGE_BUCKET", default="portfolio-media")
STORAGE_ACCESS_KEY = env("STORAGE_ACCESS_KEY", default="minioadmin")
STORAGE_SECRET_KEY = env("STORAGE_SECRET_KEY", default="minioadmin")
STORAGE_REGION = env("STORAGE_REGION", default="us-east-1")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]
CORRELATION_ID_HEADER = env("CORRELATION_ID_HEADER", default="X-Correlation-ID")
ROOT_LOGGER_NAME = "portfolio"
CORS_ALLOW_ALL_ORIGINS = False

configure_structlog(json_logs=True)

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Portfolio CMS API",
    "DESCRIPTION": "Phase 0 foundation API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
CELERY_TASK_DEFAULT_RETRY_DELAY = 60
CELERY_TASK_MAX_RETRIES = 5
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_DEFAULT_QUEUE = "maintenance"
CELERY_TASK_ROUTES: dict = {}
CELERY_TASK_QUEUES = ()
CELERY_TASK_DEFAULT_EXCHANGE = "portfolio"
CELERY_TASK_DEFAULT_EXCHANGE_TYPE = "direct"
CELERY_TASK_SEND_SENT_EVENT = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"scrub_pii": {"()": "apps.core.logging.PiiScrubFilter"}},
    "formatters": {"plain": {"format": "%(message)s"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["scrub_pii"],
            "formatter": "plain",
        }
    },
    "loggers": {"portfolio": {"handlers": ["console"], "level": "INFO"}},
}
