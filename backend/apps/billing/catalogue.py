from __future__ import annotations

from dataclasses import dataclass

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
    period: str


METRIC_REGISTRY = {
    "leads_month": MetricSpec("leads_month", "monthly"),
    "cv_renders_month": MetricSpec("cv_renders_month", "monthly"),
    "ai_credits_month": MetricSpec("ai_credits_month", "monthly"),
    "storage_bytes": MetricSpec("storage_bytes", "cumulative"),
    "portfolios": MetricSpec("portfolios", "cumulative"),
    "cv_versions": MetricSpec("cv_versions", "cumulative"),
    "blog_posts": MetricSpec("blog_posts", "cumulative"),
    "team_members": MetricSpec("team_members", "cumulative"),
}
