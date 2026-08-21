from __future__ import annotations

from django.db import models, transaction

from apps.accounts.models import Account
from apps.core.managers import AccountScopedManager
from apps.core.models import BaseModel
from apps.core.slug_registry import validate_reserved_slug


class Portfolio(BaseModel):
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

    objects = AccountScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        default_manager_name = "objects"
        indexes = [models.Index(fields=["publication_state", "-published_at"])]

    def save(self, *args, **kwargs):
        validate_reserved_slug(self.slug)
        with transaction.atomic():
            if not self._state.adding:
                previous = type(self).all_objects.get(pk=self.pk)
                if previous.slug != self.slug:
                    validate_portfolio_slug(self.slug, self.pk)
                    PortfolioSlugHistory.objects.get_or_create(
                        portfolio=self,
                        old_slug=previous.slug,
                    )
            else:
                validate_portfolio_slug(self.slug, None)
            return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class PortfolioSlugHistory(BaseModel):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="slug_history")
    old_slug = models.SlugField(max_length=80, unique=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["portfolio", "-changed_at"])]


def validate_portfolio_slug(slug: str, portfolio_id) -> None:
    validate_reserved_slug(slug)
    collision = PortfolioSlugHistory.objects.filter(old_slug=slug)
    if portfolio_id is not None:
        collision = collision.exclude(portfolio_id=portfolio_id)
    if collision.exists():
        raise ValueError("slug was previously used by another portfolio")
