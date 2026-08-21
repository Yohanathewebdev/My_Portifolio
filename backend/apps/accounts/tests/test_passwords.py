import hashlib
from unittest.mock import patch
from urllib.error import URLError

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.accounts.passwords import HIBPPasswordChecker, validate_password_not_breached


def test_hibp_checker_uses_range_prefix_and_matches_suffix():
    suffix = hashlib.sha1(b"password").hexdigest().upper()[5:]
    with patch(
        "apps.accounts.passwords.urllib.request.urlopen",
        return_value=_Response(f"{suffix}:2\n"),
    ) as open_url:
        assert HIBPPasswordChecker().is_breached("password") is True
        request = open_url.call_args.args[0]
        assert request.full_url.endswith("range/5BAA6")


def test_hibp_provider_failure_fails_open():
    with patch(
        "apps.accounts.passwords.urllib.request.urlopen",
        side_effect=URLError("offline"),
    ):
        validate_password_not_breached("password")


class _Response:
    def __init__(self, body: str):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body.encode()


class FakeBreachedChecker:
    def is_breached(self, password: str) -> bool:
        return password == "compromised"


class FakeUnavailableChecker:
    def is_breached(self, password: str) -> bool:
        raise OSError("provider unavailable")


def test_configured_checker_rejects_reported_password():
    with (
        override_settings(
            BREACHED_PASSWORD_CHECK_ENABLED=True,
            BREACHED_PASSWORD_CHECKER=("apps.accounts.tests.test_passwords.FakeBreachedChecker"),
        ),
        pytest.raises(ValidationError),
    ):
        validate_password_not_breached("compromised")


def test_configured_checker_provider_error_fails_open():
    with override_settings(
        BREACHED_PASSWORD_CHECK_ENABLED=True,
        BREACHED_PASSWORD_CHECKER=("apps.accounts.tests.test_passwords.FakeUnavailableChecker"),
    ):
        validate_password_not_breached("any-password")
