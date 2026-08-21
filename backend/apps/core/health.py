from __future__ import annotations

from urllib.request import urlopen

import redis
from celery import current_app
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from .views import PublicReadOnlyView


@extend_schema(exclude=True)
class HealthzView(PublicReadOnlyView, APIView):
    permission_classes = []

    def get(self, request):
        return JsonResponse({"status": "ok"})


@extend_schema(exclude=True)
class ReadyzView(PublicReadOnlyView, APIView):
    permission_classes = []

    def get(self, request):
        checks = {}
        try:
            connection.ensure_connection()
            checks["db"] = "ok"
        except Exception:
            checks["db"] = "error"
        try:
            redis.Redis.from_url(settings.REDIS_URL).ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"
        try:
            with urlopen(f"{settings.STORAGE_ENDPOINT}/minio/health/live", timeout=2):
                checks["storage"] = "ok"
        except Exception:
            checks["storage"] = "error"
        try:
            broker = current_app.connection_for_read()
            broker.ensure_connection(max_retries=1)
            broker.close()
            checks["broker"] = "ok"
        except Exception:
            checks["broker"] = "error"
        ready = all(value == "ok" for value in checks.values())
        return JsonResponse(
            {"status": "ok" if ready else "error", "checks": checks},
            status=200 if ready else 503,
        )


healthz = HealthzView.as_view()
readyz = ReadyzView.as_view()
