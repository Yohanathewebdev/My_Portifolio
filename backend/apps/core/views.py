from __future__ import annotations

from typing import Protocol, cast

from django.conf import settings
from django.db import models
from django.utils.module_loading import import_string
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from .managers import AccountScopedManager, PortfolioScopedManager


class PortfolioResolver(Protocol):
    def __call__(self, request: Request) -> object: ...


class SerializerWithModel(Protocol):
    class Meta:
        model: type[models.Model]


class ModelWithScopedManager(Protocol):
    objects: PortfolioScopedManager


class ModelWithAccountScopedManager(Protocol):
    objects: AccountScopedManager


def default_portfolio_resolver(request: Request) -> object:
    resolver = getattr(request, "portfolio_resolver", None)
    if callable(resolver):
        return cast(PortfolioResolver, resolver)(request)
    return import_string(settings.PORTFOLIO_RESOLVER)(request)


class PortfolioScopedViewSet(GenericViewSet):
    portfolio_resolver = staticmethod(default_portfolio_resolver)

    def get_portfolio(self) -> object:
        return self.portfolio_resolver(self.request)

    def get_queryset(self) -> models.QuerySet[models.Model]:
        serializer_class = cast(type[SerializerWithModel], self.get_serializer_class())
        model = cast(type[ModelWithScopedManager], serializer_class.Meta.model)
        return model.objects.for_portfolio(self.get_portfolio())


class AccountScopedViewSet(GenericViewSet):
    @staticmethod
    def account_resolver(request: Request) -> object:
        return import_string(settings.ACCOUNT_RESOLVER)(request)

    def get_accounts(self) -> object:
        return self.account_resolver(self.request)

    def get_request_account(self) -> object:
        return import_string(settings.ACCOUNT_REQUEST_RESOLVER)(self.request)

    def get_request_role(self) -> str:
        return import_string(settings.MEMBERSHIP_ROLE_RESOLVER)(self.request)

    def get_permissions(self):
        if getattr(self, "kwargs", {}).get("account_id"):
            self.get_request_account()
        return super().get_permissions()

    def get_queryset(self) -> models.QuerySet[models.Model]:
        serializer_class = cast(type[SerializerWithModel], self.get_serializer_class())
        model = cast(type[ModelWithAccountScopedManager], serializer_class.Meta.model)
        return model.objects.for_accounts(self.get_accounts())


class PublicReadOnlyView:
    """Marker for views intentionally accessible without portfolio ownership."""

    permission_classes = [AllowAny]
