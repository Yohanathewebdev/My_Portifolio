from types import SimpleNamespace
from typing import Any, cast

import pytest
from django.db import models
from django.urls import path
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from apps.core.managers import PortfolioScopedManager, UnscopedQueryError
from apps.core.scoping import check_urlconf
from apps.core.views import PortfolioScopedViewSet


class ScopedRecord(models.Model):
    portfolio = models.UUIDField()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        app_label = "core"
        managed = False

    def __str__(self):
        return str(self.pk)


def test_unscoped_manager_operations_fail_loudly():
    manager = PortfolioScopedManager()
    for operation in (manager.all, manager.filter, manager.get):
        with pytest.raises(UnscopedQueryError):
            operation()


def test_queryset_scope_and_explicit_escape_hatch():
    manager = PortfolioScopedManager()
    manager.model = ScopedRecord
    with pytest.raises(ValueError):
        manager.for_portfolio(None)
    with pytest.raises(ValueError):
        manager.unscoped_explicit(reason="")
    scoped = manager.for_portfolio(SimpleNamespace(pk="00000000-0000-0000-0000-000000000001"))
    assert str(scoped._portfolio_scope) == "00000000-0000-0000-0000-000000000001"
    explicit = manager.unscoped_explicit(reason="scheduled maintenance")
    assert explicit._explicit_unscoped_reason == "scheduled maintenance"


def test_queryset_operations_require_scope():
    queryset = manager_queryset()
    with pytest.raises(UnscopedQueryError):
        list(queryset)
    with pytest.raises(UnscopedQueryError):
        bool(queryset)
    with pytest.raises(UnscopedQueryError):
        queryset.get()
    with pytest.raises(UnscopedQueryError):
        queryset.count()
    with pytest.raises(UnscopedQueryError):
        queryset.exists()


def manager_queryset():
    from apps.core.managers import PortfolioScopedQuerySet

    return PortfolioScopedQuerySet(model=ScopedRecord)


class DeliberatelyUnscopedViewSet(ViewSet):
    def list(self, request):
        return Response([])


class ScopedFixtureViewSet(PortfolioScopedViewSet):
    def list(self, request):
        return Response([])


class FixtureView(APIView):
    def get(self, request):
        return Response({})


def test_scoping_gate_reports_deliberately_unscoped_fixture():
    fixture = SimpleNamespace(
        urlpatterns=[
            path("bad/", DeliberatelyUnscopedViewSet.as_view({"get": "list"}), name="bad"),
            path("good/", ScopedFixtureViewSet.as_view({"get": "list"}), name="good"),
        ]
    )
    violations = check_urlconf(fixture, allowlist={})
    assert len(violations) == 1
    assert violations[0].route == "bad/"
    assert "DeliberatelyUnscopedViewSet" in violations[0].view_name


def test_production_urlconf_has_no_scoping_violations():
    import config.urls as urlconf

    assert check_urlconf(urlconf) == []


def test_scoping_gate_walks_nested_urlresolver():
    from django.urls import include

    nested = SimpleNamespace(
        urlpatterns=[
            path("bad/", DeliberatelyUnscopedViewSet.as_view({"get": "list"}), name="nested-bad")
        ]
    )
    fixture = SimpleNamespace(urlpatterns=[path("nested/", include(nested.urlpatterns))])
    violations = check_urlconf(fixture, allowlist={})
    assert violations[0].route == "nested/bad/"


def test_portfolio_viewset_uses_pluggable_resolver():
    view = ScopedFixtureViewSet()
    request = cast(Any, APIRequestFactory().get("/"))
    request.portfolio_resolver = lambda _: "portfolio-id"
    view.request = request
    assert view.get_portfolio() == "portfolio-id"
