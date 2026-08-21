from types import SimpleNamespace
from typing import Any, cast

import pytest
from django.db.models import Count
from django.urls import path
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from apps.accounts.factories import AccountFactory
from apps.accounts.models import Account
from apps.core.managers import PortfolioScopedManager, UnscopedQueryError
from apps.core.scoping import check_urlconf
from apps.core.views import PortfolioScopedViewSet
from apps.portfolios.models import Portfolio
from apps.test_models.models import ScopedRecord


def make_account() -> Account:
    return cast(Account, AccountFactory())


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
    with pytest.raises(UnscopedQueryError):
        queryset.first()
    with pytest.raises(UnscopedQueryError):
        queryset[0]
    with pytest.raises(UnscopedQueryError):
        list(queryset.values_list("id", flat=True))
    with pytest.raises(UnscopedQueryError):
        queryset.aggregate(total=Count("id"))
    with pytest.raises(UnscopedQueryError):
        queryset.update(name="blocked")
    with pytest.raises(UnscopedQueryError):
        queryset.delete()
    with pytest.raises(UnscopedQueryError):
        queryset.in_bulk()


def manager_queryset():
    from apps.core.managers import PortfolioScopedQuerySet

    return PortfolioScopedQuerySet(model=ScopedRecord)


@pytest.mark.django_db
def test_scoped_queryset_operations_execute_against_real_model():
    portfolio = Portfolio.all_objects.create(
        account=make_account(),
        title="Photographer",
        slug="photographer",
    )
    first = cast(
        ScopedRecord,
        ScopedRecord.objects.create_for_portfolio(portfolio, name="First"),
    )
    second = cast(
        ScopedRecord,
        ScopedRecord.objects.create_for_portfolio(portfolio, name="Second"),
    )
    queryset = ScopedRecord.objects.for_portfolio(portfolio).order_by("name")

    assert queryset.first() == first
    assert queryset[0] == first
    assert list(queryset.values_list("name", flat=True)) == ["First", "Second"]
    assert queryset.aggregate(total=Count("id")) == {"total": 2}
    assert queryset.filter(pk=second.pk).update(name="Updated") == 1
    assert queryset.filter(pk=second.pk).delete()[0] == 1


@pytest.mark.django_db
def test_real_model_write_paths_refresh_soft_delete_cascade_and_related_scope():
    portfolio = Portfolio.all_objects.create(
        account=make_account(),
        title="Consultant",
        slug="consultant",
    )
    record = cast(
        ScopedRecord,
        ScopedRecord.objects.create_for_portfolio(portfolio, name="Profile"),
    )
    assert record.portfolio_id == portfolio.pk

    record.refresh_from_db()
    assert record.name == "Profile"
    assert list(portfolio.scopedrecord_set.all()) == [record]

    record.delete()
    assert not ScopedRecord.objects.for_portfolio(portfolio).filter(pk=record.pk).exists()
    assert ScopedRecord.all_objects.filter(pk=record.pk).exists()

    second = cast(
        ScopedRecord,
        ScopedRecord.objects.create_for_portfolio(portfolio, name="Cascade"),
    )
    portfolio.delete()
    assert not ScopedRecord.all_objects.filter(pk=second.pk).exists()


@pytest.mark.django_db
def test_real_model_unscoped_read_still_fails():
    Portfolio.all_objects.create(
        account=make_account(),
        title="Engineer",
        slug="engineer",
    )
    with pytest.raises(UnscopedQueryError):
        ScopedRecord.objects.all()


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
