from __future__ import annotations

from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .managers import UnscopedQueryError


class EntitlementExceeded(exceptions.APIException):
    status_code = 402
    default_code = "entitlement_exceeded"

    def __init__(
        self,
        feature: str,
        limit: int | str,
        usage: int | str,
        upgrade_url: str | None = None,
    ):
        self.feature, self.limit, self.usage, self.upgrade_url = feature, limit, usage, upgrade_url
        super().__init__("The account entitlement has been exceeded.")


class ConflictError(exceptions.APIException):
    status_code = 409
    default_code = "conflict"

    def __init__(
        self,
        detail: str = "The resource version conflicts.",
        current_version: int | None = None,
        expected_version: int | None = None,
    ):
        self.current_version = current_version
        self.expected_version = expected_version
        super().__init__(detail)


def exception_handler(exc: Exception, context: dict[str, object]) -> Response:
    response = drf_exception_handler(exc, context)
    request = context["request"]
    meta = getattr(request, "META", {})
    correlation_id = getattr(request, "correlation_id", "") or meta.get("HTTP_X_CORRELATION_ID", "")
    if isinstance(exc, UnscopedQueryError):
        status = 500
        code = "internal_error"
        message = "An internal error occurred."
        fields: dict[str, object] = {}
    elif response is None:
        status = 500
        code = "internal_error"
        message = "An internal error occurred."
        fields = {}
    else:
        status = response.status_code
        code = getattr(exc, "default_code", "error")
        detail = response.data.get("detail", response.data)
        message = str(detail) if isinstance(detail, str) else "Request failed."
        fields = response.data if isinstance(response.data, dict) else {}
        fields.pop("detail", None)
        if isinstance(exc, EntitlementExceeded):
            fields = {
                "feature": exc.feature,
                "limit": exc.limit,
                "usage": exc.usage,
                "upgrade_url": exc.upgrade_url,
            }
        elif isinstance(exc, ConflictError):
            fields = {
                "current_version": exc.current_version,
                "expected_version": exc.expected_version,
            }
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "fields": fields,
                "correlation_id": correlation_id,
            }
        },
        status=status,
        headers=getattr(response, "headers", None),
    )
