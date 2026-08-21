from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.urls import URLResolver

from .views import PortfolioScopedViewSet, PublicReadOnlyView

SCOPING_ALLOWLIST = {
    "healthz": "Liveness endpoint has no tenant data.",
    "readyz": "Readiness endpoint reports infrastructure dependencies only.",
    "schema": "OpenAPI schema is a framework metadata endpoint.",
    "swagger-ui": "OpenAPI documentation is a framework metadata endpoint.",
}


@dataclass(frozen=True)
class ScopingViolation:
    route: str
    view_name: str
    reason: str = ""


def _patterns(urlpatterns: Iterable, prefix: str = ""):
    for pattern in urlpatterns:
        route = f"{prefix}{pattern.pattern}"
        if isinstance(pattern, URLResolver):
            yield from _patterns(pattern.url_patterns, route)
        else:
            yield route, pattern


def check_urlconf(urlconf, allowlist: dict[str, str] | None = None) -> list[ScopingViolation]:
    allowlist = SCOPING_ALLOWLIST if allowlist is None else allowlist
    violations = []
    for route, pattern in _patterns(urlconf.urlpatterns):
        callback = pattern.callback
        view_cls = getattr(callback, "cls", None)
        view_name = getattr(view_cls, "__name__", getattr(callback, "__name__", repr(callback)))
        if pattern.name in allowlist:
            continue
        if view_cls and (
            issubclass(view_cls, PortfolioScopedViewSet) or issubclass(view_cls, PublicReadOnlyView)
        ):
            continue
        violations.append(ScopingViolation(route, view_name))
    return violations
