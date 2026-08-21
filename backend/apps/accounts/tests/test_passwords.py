import hashlib
from unittest.mock import patch
from urllib.error import URLError

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
