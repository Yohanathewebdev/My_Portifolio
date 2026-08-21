from __future__ import annotations

from datetime import date

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from apps.core.exceptions import EntitlementExceeded

from .catalogue import ENTITLEMENT_REGISTRY, FREE_ENTITLEMENTS, METRIC_REGISTRY
from .models import Subscription, UsageCounter

_CACHE_TTL = 60


def _ensure_metric(metric: str) -> None:
    if metric not in METRIC_REGISTRY:
        raise ValueError(f"unknown entitlement metric: {metric}")


def _period_start(metric: str, today: date | None = None) -> date:
    _ensure_metric(metric)
    spec = METRIC_REGISTRY[metric]
    if spec.period == "cumulative":
        return date(1970, 1, 1)
    current = today or timezone.now().date()
    return current.replace(day=1)


def measure_portfolios(account) -> int:
    from apps.portfolios.models import Portfolio

    return Portfolio.all_objects.filter(account_id=account.id, is_deleted=False).count()


def measure_storage_bytes(account) -> int:
    return 0


def measure_cv_versions(account) -> int:
    return 0


def measure_blog_posts(account) -> int:
    return 0


def measure_team_members(account) -> int:
    from apps.accounts.models import AccountMembership

    return AccountMembership.all_objects.filter(
        account_id=account.id,
        accepted_at__isnull=False,
    ).count()


def _measure(account, metric: str) -> int:
    spec = METRIC_REGISTRY[metric]
    if spec.measurement is None:
        raise ValueError(f"no measurement configured for {metric}")
    return import_string(spec.measurement)(account)


def _resolved(account) -> dict[str, object]:
    cache_key = f"entitlements:{account.id}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return cached
    resolved: dict[str, object] = dict(FREE_ENTITLEMENTS)
    try:
        subscription = account.subscription
    except Subscription.DoesNotExist:
        subscription = None
    if subscription is not None:
        resolved.update(subscription.plan.entitlements)
    resolved.update(account.entitlement_overrides or {})
    cache.set(cache_key, resolved, _CACHE_TTL)
    return resolved


def features(account) -> frozenset[str]:
    return frozenset(
        key
        for key, value in _resolved(account).items()
        if key in ENTITLEMENT_REGISTRY
        and ENTITLEMENT_REGISTRY[key].kind == "feature"
        and value is True
    )


def has(account, feature: str) -> bool:
    spec = ENTITLEMENT_REGISTRY.get(feature)
    if spec is None:
        return False
    value = _resolved(account).get(feature)
    if spec.kind == "feature":
        return value is True
    return value == "unlimited" or (isinstance(value, int | float) and value > 0)


def limit(account, metric: str) -> int | None:
    spec = ENTITLEMENT_REGISTRY.get(metric)
    if spec is None or spec.kind != "limit":
        raise ValueError(f"unknown entitlement limit: {metric}")
    value = _resolved(account).get(metric)
    if value in (None, "unlimited"):
        return None
    if isinstance(value, int | str):
        return int(value)
    raise ValueError(f"invalid entitlement limit for {metric}")


def usage(account, metric: str) -> int:
    _ensure_metric(metric)
    if METRIC_REGISTRY[metric].period == "cumulative":
        return _measure(account, metric)
    return (
        UsageCounter.objects.filter(
            account=account,
            metric=metric,
            period_start=_period_start(metric),
        )
        .values_list("value", flat=True)
        .first()
        or 0
    )


@transaction.atomic
def check_and_consume(account, metric: str, amount: int = 1) -> None:
    _ensure_metric(metric)
    if amount < 1:
        raise ValueError("amount must be positive")
    if METRIC_REGISTRY[metric].period == "cumulative":
        locked_account = type(account).all_objects.select_for_update().get(pk=account.pk)
        current = usage(locked_account, metric)
        maximum = limit(locked_account, metric)
        if maximum is not None and current + amount > maximum:
            raise EntitlementExceeded(metric, maximum, current)
        return
    period_start = _period_start(metric)
    counter, _ = UsageCounter.objects.get_or_create(
        account=account,
        metric=metric,
        period_start=period_start,
        defaults={"value": 0},
    )
    counter = UsageCounter.objects.select_for_update().get(pk=counter.pk)
    current = counter.value
    maximum = limit(account, metric)
    if maximum is not None and current + amount > maximum:
        raise EntitlementExceeded(metric, maximum, current)
    counter.value = current + amount
    counter.save(update_fields=["value", "updated_at"])
