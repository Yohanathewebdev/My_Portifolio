from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ValidationError


class BreachedPasswordChecker(Protocol):
    def is_breached(self, password: str) -> bool: ...


class HIBPPasswordChecker:
    timeout = 2.0

    def is_breached(self, password: str) -> bool:
        digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = digest[:5], digest[5:]
        request = urllib.request.Request(
            f"https://api.pwnedpasswords.com/range/{prefix}",
            headers={"Add-Padding": "true", "User-Agent": "portfolio-cms"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except (OSError, urllib.error.URLError):
            return False
        return any(line.split(":", 1)[0].strip() == suffix for line in body.splitlines())


def validate_password_not_breached(password: str, user=None) -> None:
    if not getattr(settings, "BREACHED_PASSWORD_CHECK_ENABLED", True):
        return
    checker: BreachedPasswordChecker = HIBPPasswordChecker()
    if checker.is_breached(password):
        raise ValidationError("This password has appeared in a data breach.")
