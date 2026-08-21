from __future__ import annotations

import uuid

import structlog
from django.conf import settings


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header = settings.CORRELATION_ID_HEADER
        correlation_id = request.headers.get(header) or str(uuid.uuid4())
        request.correlation_id = correlation_id
        previous_context = structlog.contextvars.get_contextvars()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        try:
            response = self.get_response(request)
            response[header] = correlation_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()
            if previous_context:
                structlog.contextvars.bind_contextvars(**previous_context)
