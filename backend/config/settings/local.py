from .base import *

SECRET_KEY = env("DJANGO_SECRET_KEY", default="phase-0-insecure-development-key")
AUTH_JWT_SIGNING_KEY = env("AUTH_JWT_SIGNING_KEY", default=SECRET_KEY)

DEBUG = True
configure_structlog(json_logs=False)
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env("EMAIL_PORT", default=1025)
