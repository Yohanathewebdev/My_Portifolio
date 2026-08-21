from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FREE_ENTITLEMENTS = {
    "portfolios": 1,
    "storage_bytes": 250 * 1024 * 1024,
    "custom_domain": False,
    "premium_themes": False,
    "remove_branding": False,
    "cv_versions": 1,
    "cv_renders_month": 5,
    "docx_export": False,
    "leads_month": 20,
    "lead_retention_days": 90,
    "analytics_history_days": 7,
    "revision_history": 5,
    "scheduled_publishing": False,
    "preview_links": 1,
    "team_members": 1,
    "blog_posts": 10,
    "api_access": False,
    "ai_credits_month": 0,
}

PRO_ENTITLEMENTS = {
    **FREE_ENTITLEMENTS,
    "portfolios": 3,
    "storage_bytes": 5 * 1024 * 1024 * 1024,
    "custom_domain": 1,
    "premium_themes": True,
    "remove_branding": True,
    "cv_versions": 10,
    "cv_renders_month": 100,
    "docx_export": True,
    "leads_month": 500,
    "lead_retention_days": 730,
    "analytics_history_days": 365,
    "revision_history": 50,
    "scheduled_publishing": True,
    "preview_links": 10,
    "team_members": 1,
    "blog_posts": "unlimited",
    "ai_credits_month": 100,
}

STUDIO_ENTITLEMENTS = {
    **PRO_ENTITLEMENTS,
    "portfolios": 10,
    "storage_bytes": 25 * 1024 * 1024 * 1024,
    "custom_domain": 10,
    "cv_versions": "unlimited",
    "cv_renders_month": 500,
    "leads_month": "unlimited",
    "lead_retention_days": "unlimited",
    "analytics_history_days": "unlimited",
    "revision_history": "unlimited",
    "preview_links": "unlimited",
    "team_members": 10,
}


@dataclass(frozen=True)
class MetricSpec:
    key: str
    period: Literal["monthly", "cumulative"]
    measurement: str | None = None


@dataclass(frozen=True)
class EntitlementSpec:
    key: str
    kind: Literal["feature", "limit"]


METRIC_REGISTRY = {
    "leads_month": MetricSpec("leads_month", "monthly"),
    "cv_renders_month": MetricSpec("cv_renders_month", "monthly"),
    "ai_credits_month": MetricSpec("ai_credits_month", "monthly"),
    "storage_bytes": MetricSpec(
        "storage_bytes", "cumulative", "apps.billing.entitlements.measure_storage_bytes"
    ),
    "portfolios": MetricSpec(
        "portfolios", "cumulative", "apps.billing.entitlements.measure_portfolios"
    ),
    "cv_versions": MetricSpec(
        "cv_versions", "cumulative", "apps.billing.entitlements.measure_cv_versions"
    ),
    "blog_posts": MetricSpec(
        "blog_posts", "cumulative", "apps.billing.entitlements.measure_blog_posts"
    ),
    "team_members": MetricSpec(
        "team_members", "cumulative", "apps.billing.entitlements.measure_team_members"
    ),
}

ENTITLEMENT_REGISTRY = {
    key: EntitlementSpec(key, "feature")
    for key in (
        "premium_themes",
        "remove_branding",
        "docx_export",
        "scheduled_publishing",
        "api_access",
    )
}
ENTITLEMENT_REGISTRY.update(
    {
        key: EntitlementSpec(key, "limit")
        for key in (
            "portfolios",
            "storage_bytes",
            "custom_domain",
            "cv_versions",
            "cv_renders_month",
            "leads_month",
            "lead_retention_days",
            "analytics_history_days",
            "revision_history",
            "preview_links",
            "team_members",
            "blog_posts",
            "ai_credits_month",
        )
    }
)
