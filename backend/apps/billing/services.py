from __future__ import annotations

from typing import Protocol

from django.core.cache import cache

from apps.accounts.models import Account
from apps.core.audit import record_audit

from .models import Plan, Subscription


def invalidate_entitlements(account_id) -> None:
    cache.delete(f"entitlements:{account_id}")


def free_plan() -> Plan:
    return Plan.objects.get(code="free")


def invalidate_subscription(account) -> None:
    invalidate_entitlements(account.id)


def invalidate_account_overrides(account) -> None:
    invalidate_entitlements(account.id)


def invalidate_plan(plan) -> None:
    for account_id in Subscription.objects.filter(plan=plan).values_list("account_id", flat=True):
        invalidate_entitlements(account_id)


def update_subscription(subscription: Subscription, actor=None, **changes) -> Subscription:
    before = {field: getattr(subscription, field) for field in changes}
    for field, value in changes.items():
        setattr(subscription, field, value)
    subscription.save(update_fields=[*changes, "updated_at"])
    invalidate_subscription(subscription.account)
    record_audit(
        action="subscription_updated",
        target=subscription,
        actor=actor,
        account_id=subscription.account_id,
        before=before,
        after={field: getattr(subscription, field) for field in changes},
    )
    return subscription


def update_plan_entitlements(plan: Plan, entitlements: dict[str, object], actor=None) -> Plan:
    before = plan.entitlements
    plan.entitlements = entitlements
    plan.save(update_fields=["entitlements", "updated_at"])
    invalidate_plan(plan)
    record_audit(
        action="plan_entitlements_updated",
        target=plan,
        actor=actor,
        after={"entitlements": entitlements},
        before={"entitlements": before},
    )
    return plan


def update_account_overrides(account: Account, overrides: dict[str, object], actor=None) -> Account:
    before = account.entitlement_overrides
    account.entitlement_overrides = overrides
    account.save(update_fields=["entitlement_overrides", "updated_at"])
    invalidate_entitlements(account.id)
    record_audit(
        action="account_entitlement_overrides_updated",
        target=account,
        actor=actor,
        account_id=account.id,
        before={"entitlement_overrides": before},
        after={"entitlement_overrides": overrides},
    )
    return account


class PaymentProvider(Protocol):
    def create_customer(self, account) -> str: ...

    def start_checkout(self, account, plan, success_url: str, cancel_url: str) -> str: ...

    def open_billing_portal(self, account, return_url: str) -> str: ...

    def cancel(self, subscription, at_period_end: bool) -> None: ...

    def parse_webhook(self, request): ...
