from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.urls import URLResolver
from rest_framework.permissions import AllowAny

from .views import AccountScopedViewSet, NonTenantView, PortfolioScopedViewSet, PublicReadOnlyView

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


@dataclass(frozen=True)
class AuthenticationViolation:
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
        if pattern.name in allowlist or view_name == "APIRootView":
            continue
        if view_cls and (
            issubclass(view_cls, PortfolioScopedViewSet)
            or issubclass(view_cls, PublicReadOnlyView)
            or issubclass(view_cls, AccountScopedViewSet)
            or issubclass(view_cls, NonTenantView)
        ):
            continue
        violations.append(
            ScopingViolation(
                route,
                view_name,
                "view is not portfolio-scoped, declared public, or explicitly allowlisted",
            )
        )
    return violations


def check_authentication_urlconf(urlconf) -> list[AuthenticationViolation]:
    violations = []
    for route, pattern in _patterns(urlconf.urlpatterns):
        callback = pattern.callback
        view_cls = getattr(callback, "cls", None)
        view_name = getattr(view_cls, "__name__", getattr(callback, "__name__", repr(callback)))
        if view_cls and issubclass(view_cls, PublicReadOnlyView):
            continue
        permission_classes = getattr(view_cls, "permission_classes", None)
        if permission_classes and not any(
            issubclass(permission_class, AllowAny) for permission_class in permission_classes
        ):
            continue
        violations.append(
            AuthenticationViolation(
                route,
                view_name,
                "view must require authentication or inherit PublicReadOnlyView",
            )
        )
    return violations
