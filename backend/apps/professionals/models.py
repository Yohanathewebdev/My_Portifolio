from django.db import models

from apps.core.models import BaseModel


class Profession(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    suggestion_config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["sort_order", "name"]


class PortfolioProfession(BaseModel):
    portfolio = models.ForeignKey(
        "portfolios.Portfolio", on_delete=models.CASCADE, related_name="profession_assignments"
    )
    profession = models.ForeignKey(Profession, on_delete=models.PROTECT, related_name="portfolio_links")
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "profession"], name="unique_portfolio_profession"),
            models.UniqueConstraint(
                fields=["portfolio"], condition=models.Q(is_primary=True), name="one_primary_profession"
            ),
        ]
        ordering = ["display_order", "created_at"]
