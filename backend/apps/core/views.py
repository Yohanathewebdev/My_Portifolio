from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet


def default_portfolio_resolver(request) -> Any:
    resolver: Callable[[Any], Any] | None = getattr(request, "portfolio_resolver", None)
    if resolver is None:
        raise RuntimeError("No portfolio resolver is configured for this request")
    return resolver(request)


class PortfolioScopedViewSet(GenericViewSet):
    portfolio_resolver = staticmethod(default_portfolio_resolver)

    def get_portfolio(self):
        return self.portfolio_resolver(self.request)

    def get_queryset(self):
        model = self.get_serializer_class().Meta.model  # type: ignore[attr-defined]
        return model.objects.for_portfolio(self.get_portfolio())


class PublicReadOnlyView:
    """Marker for views intentionally accessible without portfolio ownership."""

    permission_classes = [AllowAny]
