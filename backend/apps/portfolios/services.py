from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.billing.entitlements import check_and_consume
from apps.core.audit import record_audit
from apps.core.exceptions import ConflictError

from .models import Portfolio

LEGAL_TRANSITIONS = {
    "draft": {"published", "suspended"},
    "published": {"unpublished", "suspended"},
    "unpublished": {"published", "suspended"},
    "suspended": {"unpublished"},
}


@transaction.atomic
def create_portfolio(*, account, title: str, slug: str, actor=None) -> Portfolio:
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
def transition_publication(*, portfolio: Portfolio, target: str, platform_actor: bool = False):
    source = portfolio.publication_state
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
    return portfolio
