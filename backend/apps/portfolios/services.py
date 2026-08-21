from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.billing.entitlements import check_and_consume
from apps.core.audit import record_audit
from apps.core.exceptions import ConflictError
from apps.core.slug_registry import validate_reserved_slug

from .models import Portfolio, PortfolioSlugHistory

LEGAL_TRANSITIONS = {
    "draft": {"published", "suspended"},
    "published": {"unpublished", "suspended"},
    "unpublished": {"published", "suspended"},
    "suspended": {"unpublished"},
}


@transaction.atomic
def create_portfolio(*, account, title: str, slug: str, actor=None) -> Portfolio:
    validate_portfolio_slug(slug, None)
    check_and_consume(account, "portfolios")
    portfolio = Portfolio.all_objects.create(account=account, title=title, slug=slug)
    record_audit(
        action="portfolio_created",
        target=portfolio,
        actor=actor,
        account_id=account.id,
        portfolio_id=portfolio.id,
    )
    return portfolio


@transaction.atomic
def update_portfolio(*, portfolio: Portfolio, actor=None, **changes) -> Portfolio:
    previous_slug = portfolio.slug
    new_slug = changes.get("slug", previous_slug)
    if new_slug != previous_slug:
        validate_portfolio_slug(new_slug, portfolio.pk)
    for field, value in changes.items():
        setattr(portfolio, field, value)
    portfolio.save(update_fields=[*changes, "updated_at"])
    if new_slug != previous_slug:
        PortfolioSlugHistory.objects.get_or_create(
            portfolio=portfolio,
            old_slug=previous_slug,
        )
        record_audit(
            action="portfolio_slug_changed",
            target=portfolio,
            actor=actor,
            account_id=portfolio.account_id,
            portfolio_id=portfolio.id,
            before={"slug": previous_slug},
            after={"slug": new_slug},
        )
    return portfolio


def validate_portfolio_slug(slug: str, portfolio_id) -> None:
    try:
        validate_reserved_slug(slug)
    except ValueError as exc:
        raise ValidationError({"slug": [str(exc)]}) from exc
    if Portfolio.all_objects.filter(slug=slug, is_deleted=False).exclude(pk=portfolio_id).exists():
        raise ValidationError({"slug": ["A portfolio already uses this slug."]})
    collision = PortfolioSlugHistory.objects.filter(old_slug=slug)
    if portfolio_id is not None:
        collision = collision.exclude(portfolio_id=portfolio_id)
    if collision.exists():
        raise ValidationError({"slug": ["This slug was previously used by another portfolio."]})


@transaction.atomic
def transition_publication(
    *, portfolio: Portfolio, target: str, platform_actor: bool = False, actor=None
):
    source = portfolio.publication_state
    if target == Portfolio.STATE_PUBLISHED and not platform_actor:
        if actor is not None and not getattr(actor, "is_email_verified", False):
            raise PermissionDenied("Email verification is required before publishing.")
    if target == Portfolio.STATE_SUSPENDED and not platform_actor:
        raise ConflictError("Only platform actors may suspend a portfolio.")
    if source == Portfolio.STATE_SUSPENDED and not platform_actor:
        raise ConflictError("Only platform actors may unsuspend a portfolio.")
    if source == Portfolio.STATE_SUSPENDED and target != Portfolio.STATE_UNPUBLISHED:
        raise ConflictError("Suspended portfolios may only be unsuspended to unpublished.")
    if target not in LEGAL_TRANSITIONS.get(source, set()):
        raise ConflictError(f"Illegal publication transition: {source} -> {target}")
    now = timezone.now()
    portfolio.publication_state = target
    if target == Portfolio.STATE_PUBLISHED:
        portfolio.published_at = now
    if target in {Portfolio.STATE_UNPUBLISHED, Portfolio.STATE_SUSPENDED}:
        portfolio.unpublished_at = now
    portfolio.save(
        update_fields=[
            "publication_state",
            "published_at",
            "unpublished_at",
            "updated_at",
        ]
    )
    record_audit(
        action="portfolio_publication_changed",
        target=portfolio,
        actor=actor,
        account_id=portfolio.account_id,
        portfolio_id=portfolio.id,
        before={"publication_state": source},
        after={"publication_state": target},
    )
    return portfolio
