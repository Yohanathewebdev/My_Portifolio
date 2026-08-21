from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from typing import cast

import pytest
from django.core.cache import cache
from django.db import close_old_connections

from apps.accounts.factories import AccountFactory
from apps.accounts.models import Account
from apps.billing.catalogue import METRIC_REGISTRY, MetricSpec
from apps.billing.entitlements import (
    _period_start,
    check_and_consume,
    features,
    has,
    limit,
    measure_blog_posts,
    measure_cv_versions,
    measure_storage_bytes,
    measure_team_members,
    usage,
)
from apps.billing.models import Plan, Subscription, UsageCounter
from apps.billing.services import (
    invalidate_account_overrides,
    invalidate_plan,
    invalidate_subscription,
    update_account_overrides,
    update_plan_entitlements,
    update_subscription,
)
from apps.core.exceptions import EntitlementExceeded
from apps.core.models import AuditLog


def make_account() -> Account:
    return cast(Account, AccountFactory())


@pytest.fixture(autouse=True)
def clear_entitlement_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_entitlement_resolution_features_limits_and_periods():
    account = make_account()
    assert "custom_domain" not in features(account)
    assert not has(account, "custom_domain")
    assert limit(account, "portfolios") == 1
    assert limit(account, "custom_domain") == 0
    assert usage(account, "portfolios") == 0
    assert _period_start("leads_month", date(2026, 8, 21)) == date(2026, 8, 1)
    assert _period_start("storage_bytes") == date(1970, 1, 1)

    plan = Plan.objects.get(code="pro")
    Subscription.objects.create(account=account, plan=plan, status=Subscription.STATUS_ACTIVE)
    cache.delete(f"entitlements:{account.id}")
    assert has(account, "custom_domain")
    assert has(account, "premium_themes")
    assert limit(account, "custom_domain") == 1
    assert limit(account, "portfolios") == 3
    assert limit(account, "blog_posts") is None
    update_account_overrides(account, {"portfolios": 1, "custom_domain": False})
    assert not has(account, "custom_domain")
    assert limit(account, "portfolios") == 1


@pytest.mark.django_db
def test_entitlement_consumption_validates_and_raises_with_upgrade_fields():
    account = make_account()
    with pytest.raises(ValueError):
        check_and_consume(account, "unknown")
    with pytest.raises(ValueError):
        check_and_consume(account, "portfolios", 0)
    account.entitlement_overrides = {"leads_month": 1}
    account.save(update_fields=["entitlement_overrides", "updated_at"])
    check_and_consume(account, "leads_month")
    with pytest.raises(EntitlementExceeded) as error:
        check_and_consume(account, "leads_month")
    assert error.value.feature == "leads_month"
    assert error.value.limit == 1
    assert error.value.usage == 1
    assert usage(account, "leads_month") == 1


@pytest.mark.django_db
def test_limit_rejects_invalid_entitlement_value():
    account = make_account()
    account.entitlement_overrides = {"portfolios": []}
    account.save(update_fields=["entitlement_overrides", "updated_at"])
    with pytest.raises(ValueError, match="invalid entitlement limit"):
        limit(account, "portfolios")


@pytest.mark.django_db
def test_measurement_registry_and_invalid_entitlement_keys():
    account = make_account()
    assert measure_storage_bytes(account) == 0
    assert measure_cv_versions(account) == 0
    assert measure_blog_posts(account) == 0
    assert measure_team_members(account) == 0
    assert has(account, "unknown_feature") is False
    with pytest.raises(ValueError, match="unknown entitlement limit"):
        limit(account, "unknown_limit")
    with pytest.raises(ValueError, match="unknown entitlement limit"):
        limit(account, "premium_themes")
    METRIC_REGISTRY["broken_metric"] = MetricSpec("broken_metric", "cumulative")
    try:
        with pytest.raises(ValueError, match="no measurement configured"):
            usage(account, "broken_metric")
    finally:
        del METRIC_REGISTRY["broken_metric"]


@pytest.mark.django_db
def test_entitlement_cache_invalidation_services():
    account = make_account()
    plan = Plan.objects.get(code="pro")
    subscription = Subscription.objects.create(
        account=account,
        plan=plan,
        status=Subscription.STATUS_ACTIVE,
    )
    assert limit(account, "portfolios") == 3
    update_subscription(subscription, status=Subscription.STATUS_SUSPENDED)
    invalidate_subscription(account)
    update_plan_entitlements(plan, {"portfolios": 4})
    invalidate_plan(plan)
    update_account_overrides(account, {"portfolios": 2})
    invalidate_account_overrides(account)
    assert limit(account, "portfolios") == 2
    assert AuditLog.objects.filter(action="subscription_updated").exists()
    assert AuditLog.objects.filter(action="plan_entitlements_updated").exists()
    assert AuditLog.objects.filter(action="account_entitlement_overrides_updated").exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_consumers_cannot_both_pass_limit():
    account = make_account()
    account.entitlement_overrides = {"leads_month": 1}
    account.save(update_fields=["entitlement_overrides", "updated_at"])
    barrier = Barrier(2)

    def consume():
        close_old_connections()
        barrier.wait()
        try:
            check_and_consume(account, "leads_month")
            return "ok"
        except EntitlementExceeded:
            return "exceeded"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: consume(), range(2)))
    assert sorted(results) == ["exceeded", "ok"]
    assert UsageCounter.objects.get(account=account, metric="leads_month").value == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_cumulative_consumers_serialize_live_portfolio_measurement():
    from apps.portfolios.services import create_portfolio

    account = make_account()
    barrier = Barrier(2)

    def create(index: int):
        close_old_connections()
        barrier.wait()
        try:
            create_portfolio(
                account=account,
                title=f"Portfolio {index}",
                slug=f"concurrent-{index}",
            )
            return "ok"
        except EntitlementExceeded:
            return "exceeded"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, range(2)))
    assert sorted(results) == ["exceeded", "ok"]
    assert usage(account, "portfolios") == 1


@pytest.mark.django_db
def test_deleting_portfolio_frees_cumulative_slot():
    from apps.portfolios.services import create_portfolio

    account = make_account()
    portfolio = create_portfolio(account=account, title="First", slug="free-slot-first")
    portfolio.delete()
    replacement = create_portfolio(
        account=account,
        title="Replacement",
        slug="free-slot-replacement",
    )
    assert replacement.is_deleted is False
    assert usage(account, "portfolios") == 1
