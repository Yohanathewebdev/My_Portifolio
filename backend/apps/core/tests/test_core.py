import logging

import pytest
from django.test import RequestFactory
from rest_framework.exceptions import NotFound

from apps.core.audit import record_audit
from apps.core.exceptions import (
    ConflictError,
    EntitlementExceeded,
    exception_handler,
)
from apps.core.logging import PiiScrubFilter
from apps.core.managers import UnscopedQueryError
from apps.core.models import AuditLog
from apps.core.pagination import StandardPagination


def test_pagination_limits():
    assert StandardPagination.page_size == 20
    assert StandardPagination.max_page_size == 100


def test_error_envelope_for_conflict():
    request = RequestFactory().get("/", HTTP_X_CORRELATION_ID="cid")
    response = exception_handler(
        ConflictError("version mismatch", current_version=4, expected_version=3),
        {"request": request},
    )
    assert response.status_code == 409
    assert response.data["error"]["code"] == "conflict"
    assert response.data["error"]["correlation_id"] == "cid"
    assert response.data["error"]["fields"] == {"current_version": 4, "expected_version": 3}


def test_entitlement_error_fields():
    request = RequestFactory().get("/")
    response = exception_handler(
        EntitlementExceeded("portfolio_count", 1, 2, "https://example.test/upgrade"),
        {"request": request},
    )
    assert response.status_code == 402
    assert response.data["error"]["fields"]["usage"] == 2


def test_internal_errors_use_generic_envelope():
    request = RequestFactory().get("/", HTTP_X_CORRELATION_ID="cid")
    response = exception_handler(RuntimeError("secret internals"), {"request": request})
    assert response.status_code == 500
    assert response.data["error"]["code"] == "internal_error"
    assert response.data["error"]["message"] == "An internal error occurred."


def test_standard_api_errors_use_same_envelope():
    request = RequestFactory().get("/")
    response = exception_handler(NotFound("missing"), {"request": request})
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_unscoped_errors_are_not_leaked():
    request = RequestFactory().get("/")
    response = exception_handler(UnscopedQueryError("table details"), {"request": request})
    assert response.status_code == 500
    assert "table details" not in str(response.data)


def test_log_scrubbing_redacts_email_and_token(caplog):
    logger = logging.getLogger("portfolio.test")
    logger.addFilter(PiiScrubFilter())
    with caplog.at_level(logging.INFO, logger="portfolio.test"):
        logger.info("email=%s token=%s", "person@example.com", "Bearer abcdefghijklmnop")
    assert "person@example.com" not in caplog.text
    assert "abcdefghijklmnop" not in caplog.text
    assert "[REDACTED_EMAIL]" in caplog.text
    assert "[REDACTED_TOKEN]" in caplog.text


@pytest.mark.django_db
def test_record_audit_creates_append_only_entry():
    target = AuditLog.objects.create(
        actor_type="system",
        action="seed",
        target_type="core.auditlog",
        target_id="target",
    )
    entry = record_audit(action="inspect", target=target, correlation_id="cid")
    assert entry.action == "inspect"
    assert entry.correlation_id == "cid"
