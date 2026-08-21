from __future__ import annotations

from typing import Protocol, cast

from django.db import models
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from .managers import PortfolioScopedManager


class PortfolioResolver(Protocol):
    def __call__(self, request: Request) -> object: ...


class SerializerWithModel(Protocol):
    class Meta:
        model: type[models.Model]


class ModelWithScopedManager(Protocol):
    objects: PortfolioScopedManager


def default_portfolio_resolver(request: Request) -> object:
    resolver = getattr(request, "portfolio_resolver", None)
    if not callable(resolver):
        raise RuntimeError("No portfolio resolver is configured for this request")
    return cast(PortfolioResolver, resolver)(request)


class PortfolioScopedViewSet(GenericViewSet):
    portfolio_resolver = staticmethod(default_portfolio_resolver)

    def get_portfolio(self) -> object:
        return self.portfolio_resolver(self.request)

    def get_queryset(self) -> models.QuerySet[models.Model]:
        serializer_class = cast(type[SerializerWithModel], self.get_serializer_class())
        model = cast(type[ModelWithScopedManager], serializer_class.Meta.model)
        return model.objects.for_portfolio(self.get_portfolio())


class PublicReadOnlyView:
    """Marker for views intentionally accessible without portfolio ownership."""

    permission_classes = [AllowAny]
