from collections.abc import Sequence

from django.core.exceptions import ImproperlyConfigured


def validate_production_security(
    *,
    debug: bool,
    secret_key: str,
    allowed_hosts: Sequence[str],
    cors_allow_all: bool,
    email_backend: str,
    email_host: str,
) -> None:
    if debug:
        raise ImproperlyConfigured("DJANGO_DEBUG must be false in production")
    if not secret_key or secret_key in {
        "change-me-in-local-development",
        "phase-0-insecure-development-key",
    }:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a secure production value")
    if len(secret_key) < 50:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be at least 50 characters")
    if "*" in allowed_hosts:
        raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must not contain '*' in production")
    if cors_allow_all:
        raise ImproperlyConfigured("CORS_ALLOW_ALL_ORIGINS must be false in production")
    if not email_backend.strip():
        raise ImproperlyConfigured("EMAIL_BACKEND must be configured in production")
    if not email_host.strip():
        raise ImproperlyConfigured("EMAIL_HOST must be configured in production")
