from .base import *

SECRET_KEY = env("DJANGO_SECRET_KEY", default="phase-0-insecure-development-key")

DEBUG = True
configure_structlog(json_logs=False)
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
