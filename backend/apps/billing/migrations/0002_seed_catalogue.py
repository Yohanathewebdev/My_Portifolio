# ruff: noqa: E501, I001
from django.db import migrations


CATALOGUE = {
    "free": {
        "name": "Free",
        "sort_order": 1,
        "entitlements": {
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
        },
    },
    "pro": {
        "name": "Pro",
        "sort_order": 2,
        "entitlements": {
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
            "api_access": False,
            "ai_credits_month": 100,
        },
    },
    "studio": {
        "name": "Studio",
        "sort_order": 3,
        "entitlements": {
            "portfolios": 10,
            "storage_bytes": 25 * 1024 * 1024 * 1024,
            "custom_domain": 10,
            "premium_themes": True,
            "remove_branding": True,
            "cv_versions": "unlimited",
            "cv_renders_month": 500,
            "docx_export": True,
            "leads_month": "unlimited",
            "lead_retention_days": "unlimited",
            "analytics_history_days": "unlimited",
            "revision_history": "unlimited",
            "scheduled_publishing": True,
            "preview_links": "unlimited",
            "team_members": 10,
            "blog_posts": "unlimited",
            "api_access": True,
            "ai_credits_month": 500,
        },
    },
}


def seed_catalogue(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for code, values in CATALOGUE.items():
        Plan.objects.update_or_create(
            code=code,
            defaults={
                **values,
                "description": f"{values['name']} plan",
                "provider_price_id": None,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("billing", "0001_initial")]

    operations = [migrations.RunPython(seed_catalogue, migrations.RunPython.noop)]
