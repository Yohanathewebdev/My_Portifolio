from __future__ import annotations

from datetime import date

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import EntitlementExceeded

from .catalogue import FREE_ENTITLEMENTS, METRIC_REGISTRY
from .models import Subscription, UsageCounter

_CACHE_TTL = 60
FEATURE_KEYS = {
    "custom_domain",
    "premium_themes",
    "remove_branding",
    "docx_export",
    "scheduled_publishing",
    "api_access",
}


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
        if key in FEATURE_KEYS and (value is True or value not in (False, 0, None, "unlimited"))
    )


def has(account, feature: str) -> bool:
    value = _resolved(account).get(feature)
    return feature in FEATURE_KEYS and value not in (False, 0, None)


def limit(account, metric: str) -> int | None:
    _ensure_metric(metric)
    value = _resolved(account).get(metric)
    if value in (None, "unlimited"):
        return None
    if isinstance(value, int | str):
        return int(value)
    raise ValueError(f"invalid entitlement limit for {metric}")


def usage(account, metric: str) -> int:
    _ensure_metric(metric)
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
