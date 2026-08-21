from __future__ import annotations

from decimal import Decimal

from django.db import models

from apps.accounts.models import Account
from apps.core.models import BaseModel


class Plan(BaseModel):
    INTERVAL_MONTH = "month"
    INTERVAL_YEAR = "year"
    INTERVAL_CHOICES = ((INTERVAL_MONTH, "Month"), (INTERVAL_YEAR, "Year"))

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default=INTERVAL_MONTH)
    price_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    price_currency = models.CharField(max_length=3, default="USD")
    is_public = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    entitlements = models.JSONField(default=dict)
    provider_price_id = models.CharField(  # noqa: DJ001
        max_length=128,
        null=True,
        blank=True,
    )


class Subscription(BaseModel):
    STATUS_TRIALING = "trialing"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_SUSPENDED = "suspended"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = (
        (STATUS_TRIALING, "Trialing"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAST_DUE, "Past due"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_CANCELED, "Canceled"),
    )

    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    provider_customer_id = models.CharField(max_length=128, blank=True)
    provider_subscription_id = models.CharField(max_length=128, blank=True)
    provider = models.CharField(max_length=32, blank=True)


class UsageCounter(BaseModel):
    METRIC_STORAGE = "storage_bytes"
    METRIC_LEADS = "leads_month"
    METRIC_CV = "cv_renders_month"
    METRIC_AI = "ai_credits_month"
    METRIC_PORTFOLIOS = "portfolios"
    METRIC_CHOICES = (
        (METRIC_STORAGE, "Storage bytes"),
        (METRIC_LEADS, "Leads this month"),
        (METRIC_CV, "CV renders this month"),
        (METRIC_AI, "AI credits this month"),
        (METRIC_PORTFOLIOS, "Portfolios"),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="usage_counters")
    metric = models.CharField(max_length=32, choices=METRIC_CHOICES)
    value = models.PositiveBigIntegerField(default=0)
    period_start = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "metric", "period_start"],
                name="unique_usage_counter_period",
            )
        ]


class BillingEvent(BaseModel):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="billing_events")
    provider = models.CharField(max_length=32)
    provider_event_id = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=100)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, default="received")
