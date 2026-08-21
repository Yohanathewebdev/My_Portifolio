from __future__ import annotations

from typing import Any

from django.db import models


class UnscopedQueryError(RuntimeError):
    """Raised when a portfolio-owned queryset is used without an explicit scope."""


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class PortfolioScopedQuerySet(models.QuerySet):
    _portfolio_scope: Any = None
    _explicit_unscoped_reason: str | None = None

    def _clone(self):
        clone = super()._clone()  # type: ignore[misc]
        clone._portfolio_scope = self._portfolio_scope
        clone._explicit_unscoped_reason = self._explicit_unscoped_reason
        return clone

    def for_portfolio(self, portfolio: Any) -> PortfolioScopedQuerySet:
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

    def _ensure_scope(self):
        if self._portfolio_scope is None and self._explicit_unscoped_reason is None:
            raise UnscopedQueryError(
                "Portfolio-owned query requires .for_portfolio(portfolio) or "
                ".unscoped_explicit(reason=...)"
            )

    def __iter__(self):
        self._ensure_scope()
        return super().__iter__()

    def __bool__(self):
        self._ensure_scope()
        return super().__bool__()

    def get(self, *args, **kwargs):
        self._ensure_scope()
        return super().get(*args, **kwargs)

    def count(self):
        self._ensure_scope()
        return super().count()

    def exists(self):
        self._ensure_scope()
        return super().exists()


class PortfolioScopedManager(models.Manager.from_queryset(PortfolioScopedQuerySet)):  # type: ignore[misc]
    def get_queryset(self):
        # Deliberately fail before constructing an executable unscoped query.
        raise UnscopedQueryError(
            "Portfolio-owned manager requires .for_portfolio(portfolio) or "
            ".unscoped_explicit(reason=...)"
        )

    def for_portfolio(self, portfolio: Any) -> PortfolioScopedQuerySet:
        queryset = super().get_queryset()
        return queryset.filter(is_deleted=False).for_portfolio(portfolio)

    def unscoped_explicit(self, *, reason: str) -> PortfolioScopedQuerySet:
        queryset = super().get_queryset()
        return queryset.filter(is_deleted=False).unscoped_explicit(reason=reason)
