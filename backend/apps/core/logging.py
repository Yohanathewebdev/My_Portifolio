from __future__ import annotations

import logging
import re
from collections.abc import Mapping

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
TOKEN_RE = re.compile(r"(?i)\b(?:bearer\s+|token[=:]\s*)[A-Z0-9._~+/=-]{8,}")


def scrub(value):
    if isinstance(value, str):
        value = TOKEN_RE.sub("[REDACTED_TOKEN]", value)
        return EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    if isinstance(value, Mapping):
        return {key: scrub(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(scrub(item) for item in value)
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value


class PiiScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = scrub(record.msg)
        record.args = scrub(record.args)
        return True
