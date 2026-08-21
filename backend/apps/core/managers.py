from __future__ import annotations

from typing import cast

from django.db import models


class UnscopedQueryError(RuntimeError):
    """Raised when a portfolio-owned queryset is used without an explicit scope."""


class SoftDeleteManager(models.Manager[models.Model]):
    def get_queryset(self) -> models.QuerySet[models.Model]:
        return super().get_queryset().filter(is_deleted=False)


class PortfolioScopedQuerySet(models.QuerySet[models.Model]):
    _portfolio_scope: object | None = None
    _explicit_unscoped_reason: str | None = None

    def _clone(self):
        clone = cast(PortfolioScopedQuerySet, super()._clone())  # type: ignore[misc]
        clone._portfolio_scope = self._portfolio_scope
        clone._explicit_unscoped_reason = self._explicit_unscoped_reason
        return clone

    def for_portfolio(self, portfolio: object) -> PortfolioScopedQuerySet:
        if portfolio is None:
            raise ValueError("portfolio is required")
        clone = self._clone()
        clone._portfolio_scope = getattr(portfolio, "pk", portfolio)
        return clone.filter(portfolio=clone._portfolio_scope)

    def unscoped_explicit(self, *, reason: str) -> PortfolioScopedQuerySet:
        if not reason or not reason.strip():
            raise ValueError("reason is required for an unscoped query")
        clone = self._clone()
        clone._explicit_unscoped_reason = reason
        return clone

    def _ensure_scope(self) -> None:
        if self._portfolio_scope is None and self._explicit_unscoped_reason is None:
            raise UnscopedQueryError(
                "Portfolio-owned query requires .for_portfolio(portfolio) or "
                ".unscoped_explicit(reason=...)"
            )

    def _fetch_all(self) -> None:
        self._ensure_scope()
        super()._fetch_all()

    def aggregate(self, *args, **kwargs):
        self._ensure_scope()
        return super().aggregate(*args, **kwargs)

    def update(self, **kwargs):
        self._ensure_scope()
        return super().update(**kwargs)

    def delete(self):
        self._ensure_scope()
        return super().delete()

    def count(self):
        self._ensure_scope()
        return super().count()

    def exists(self):
        self._ensure_scope()
        return super().exists()

    def get(self, *args, **kwargs):
        self._ensure_scope()
        return super().get(*args, **kwargs)

    def in_bulk(self, *args, **kwargs):
        self._ensure_scope()
        return super().in_bulk(*args, **kwargs)


class PortfolioScopedManager(models.Manager.from_queryset(PortfolioScopedQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> PortfolioScopedQuerySet:
        core_filters = getattr(self, "core_filters", None)
        if isinstance(core_filters, dict) and "portfolio" in core_filters:
            queryset = super().get_queryset().filter(is_deleted=False)
            return queryset.for_portfolio(core_filters["portfolio"])
        raise UnscopedQueryError(
            "Portfolio-owned manager requires .for_portfolio(portfolio) or "
            ".unscoped_explicit(reason=...)"
        )

    def for_portfolio(self, portfolio: object) -> PortfolioScopedQuerySet:
        queryset = super().get_queryset()
        return queryset.filter(is_deleted=False).for_portfolio(portfolio)

    def unscoped_explicit(self, *, reason: str) -> PortfolioScopedQuerySet:
        queryset = super().get_queryset()
        return queryset.filter(is_deleted=False).unscoped_explicit(reason=reason)

    def create_for_portfolio(self, portfolio: object, **kwargs: object) -> models.Model:
        """Create through an explicit portfolio scope.

        Use ``all_objects`` for administrative/system writes that intentionally
        bypass tenant scoping.
        """
        if portfolio is None:
            raise ValueError("portfolio is required")
        if "portfolio" in kwargs and kwargs["portfolio"] != portfolio:
            raise ValueError("portfolio argument conflicts with kwargs")
        kwargs["portfolio"] = portfolio
        instance = self.model(**kwargs)
        instance.save(using=self._db)
        return instance


class AccountScopedQuerySet(models.QuerySet[models.Model]):
    _account_scope: object | None = None

    def _clone(self):
        clone = cast(AccountScopedQuerySet, super()._clone())  # type: ignore[misc]
        clone._account_scope = self._account_scope
        return clone

    def for_accounts(self, accounts: object, *, lookup: str) -> AccountScopedQuerySet:
        if accounts is None:
            raise ValueError("accounts are required")
        clone = self._clone()
        clone._account_scope = accounts
        field_names = {field.name for field in self.model._meta.get_fields()}
        clone = clone.filter(**{lookup: accounts})
        if "is_deleted" in field_names:
            clone = clone.filter(is_deleted=False)
        return clone

    def _ensure_scope(self) -> None:
        if self._account_scope is None:
            raise UnscopedQueryError("Account-owned query requires .for_accounts(accounts)")

    def _fetch_all(self) -> None:
        self._ensure_scope()
        super()._fetch_all()

    def aggregate(self, *args, **kwargs):
        self._ensure_scope()
        return super().aggregate(*args, **kwargs)

    def update(self, **kwargs):
        self._ensure_scope()
        return super().update(**kwargs)

    def delete(self):
        self._ensure_scope()
        return super().delete()

    def count(self):
        self._ensure_scope()
        return super().count()

    def exists(self):
        self._ensure_scope()
        return super().exists()

    def get(self, *args, **kwargs):
        self._ensure_scope()
        return super().get(*args, **kwargs)

    def in_bulk(self, *args, **kwargs):
        self._ensure_scope()
        return super().in_bulk(*args, **kwargs)


class AccountScopedManager(models.Manager.from_queryset(AccountScopedQuerySet)):  # type: ignore[misc]
    scope_lookup = "account_id__in"

    def get_queryset(self) -> AccountScopedQuerySet:
        raise UnscopedQueryError("Account-owned manager requires .for_accounts(accounts)")

    def for_accounts(self, accounts: object) -> AccountScopedQuerySet:
        return super().get_queryset().for_accounts(accounts, lookup=self.scope_lookup)


class PrimaryAccountScopedManager(AccountScopedManager):
    scope_lookup = "pk__in"
