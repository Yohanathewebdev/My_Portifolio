from __future__ import annotations

from typing import ClassVar

from django.db import models

from apps.accounts.models import Account
from apps.core.managers import AccountScopedManager
from apps.core.models import BaseModel, SoftDeleteModel


class Portfolio(SoftDeleteModel):
    STATE_DRAFT = "draft"
    STATE_PUBLISHED = "published"
    STATE_UNPUBLISHED = "unpublished"
    STATE_SUSPENDED = "suspended"
    STATE_CHOICES = (
        (STATE_DRAFT, "Draft"),
        (STATE_PUBLISHED, "Published"),
        (STATE_UNPUBLISHED, "Unpublished"),
        (STATE_SUSPENDED, "Suspended"),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="portfolios")
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=200)
    publication_state = models.CharField(
        max_length=16,
        choices=STATE_CHOICES,
        default=STATE_DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    unpublished_at = models.DateTimeField(null=True, blank=True)
    active_theme_id = models.UUIDField(null=True, blank=True)
    primary_locale = models.CharField(max_length=10, default="en")
    default_currency = models.CharField(max_length=3, default="USD")
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.TextField(blank=True)
    og_image_id = models.UUIDField(null=True, blank=True)
    is_indexable = models.BooleanField(default=True)

    objects: ClassVar[AccountScopedManager] = AccountScopedManager()
    all_objects: ClassVar[models.Manager] = models.Manager()  # type: ignore[no-redef]

    class Meta:
        base_manager_name = "all_objects"
        default_manager_name = "objects"
        indexes = [models.Index(fields=["publication_state", "-published_at"])]

    def __str__(self) -> str:
        return self.title


class PortfolioSlugHistory(BaseModel):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="slug_history")
    old_slug = models.SlugField(max_length=80, unique=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["portfolio", "-changed_at"])]
