from typing import cast

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings import base
from config.settings.security import validate_production_security


def test_production_security_settings_are_safe():
    validate_production_security(
        debug=False,
        secret_key="x" * 64,
        allowed_hosts=["cms.example.com"],
        cors_allow_all=False,
        email_backend="django.core.mail.backends.smtp.EmailBackend",
        email_host="smtp.example.com",
    )


def test_base_authentication_settings_use_argon2_and_standard_validators():
    assert base.PASSWORD_HASHERS[0].endswith("Argon2PasswordHasher")
    assert len(base.AUTH_PASSWORD_VALIDATORS) == 4


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"debug": True}, "DEBUG"),
        ({"secret_key": "phase-0-insecure-development-key"}, "SECRET_KEY"),
        ({"allowed_hosts": ["*"]}, "ALLOWED_HOSTS"),
        ({"cors_allow_all": True}, "CORS_ALLOW_ALL_ORIGINS"),
        ({"email_backend": ""}, "EMAIL_BACKEND"),
        ({"email_host": ""}, "EMAIL_HOST"),
    ],
)
def test_production_security_assertions_reject_unsafe_values(kwargs, message):
    settings: dict[str, object] = {
        "debug": False,
        "secret_key": "x" * 64,
        "allowed_hosts": ["cms.example.com"],
        "cors_allow_all": False,
        "email_backend": "django.core.mail.backends.smtp.EmailBackend",
        "email_host": "smtp.example.com",
    }
    settings.update(kwargs)
    with pytest.raises(ImproperlyConfigured, match=message):
        validate_production_security(
            debug=cast(bool, settings["debug"]),
            secret_key=cast(str, settings["secret_key"]),
            allowed_hosts=cast(list[str], settings["allowed_hosts"]),
            cors_allow_all=cast(bool, settings["cors_allow_all"]),
            email_backend=cast(str, settings["email_backend"]),
            email_host=cast(str, settings["email_host"]),
        )
