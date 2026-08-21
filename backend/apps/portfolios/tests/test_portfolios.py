from typing import cast

import pytest
from rest_framework.exceptions import ValidationError

from apps.accounts.factories import AccountFactory, UserFactory
from apps.accounts.models import Account, User
from apps.core.exceptions import ConflictError
from apps.portfolios.models import Portfolio, PortfolioSlugHistory
from apps.portfolios.services import (
    LEGAL_TRANSITIONS,
    create_portfolio,
    transition_publication,
    update_portfolio,
)


def make_account() -> Account:
    return cast(Account, AccountFactory())


def make_user() -> User:
    return cast(User, UserFactory())


@pytest.mark.django_db
def test_reserved_slug_and_historical_collision_rules():
    account = make_account()
    portfolio = create_portfolio(account=account, title="One", slug="first")
    with pytest.raises(ValidationError) as reserved:
        create_portfolio(account=account, title="Reserved", slug="admin")
    assert reserved.value.status_code == 400
    update_portfolio(portfolio=portfolio, slug="second")
    assert PortfolioSlugHistory.objects.get(portfolio=portfolio, old_slug="first")
    other = make_account()
    with pytest.raises(ValidationError) as collision:
        create_portfolio(account=other, title="Collision", slug="first")
    assert collision.value.status_code == 400
    update_portfolio(portfolio=portfolio, slug="first")
    assert portfolio.slug == "first"


@pytest.mark.django_db
def test_every_legal_publication_transition_and_illegal_transition():
    account = make_account()
    actor = make_user()
    actor.is_email_verified = True
    actor.save(update_fields=["is_email_verified", "updated_at"])
    portfolio = Portfolio.all_objects.create(account=account, title="State", slug="state")
    for source, targets in LEGAL_TRANSITIONS.items():
        for target in targets:
            portfolio.publication_state = source
            portfolio.save(update_fields=["publication_state"])
            transition_publication(
                portfolio=portfolio,
                target=target,
                platform_actor=(
                    source == Portfolio.STATE_SUSPENDED or target == Portfolio.STATE_SUSPENDED
                ),
                actor=actor,
            )
            assert portfolio.publication_state == target
            if target == Portfolio.STATE_PUBLISHED:
                assert portfolio.published_at is not None
            if target in {
                Portfolio.STATE_UNPUBLISHED,
                Portfolio.STATE_SUSPENDED,
            }:
                assert portfolio.unpublished_at is not None
    portfolio.publication_state = Portfolio.STATE_DRAFT
    portfolio.save(update_fields=["publication_state"])
    with pytest.raises(ConflictError):
        transition_publication(portfolio=portfolio, target=Portfolio.STATE_UNPUBLISHED)
    with pytest.raises(ConflictError):
        transition_publication(portfolio=portfolio, target=Portfolio.STATE_SUSPENDED)
    transition_publication(
        portfolio=portfolio,
        target=Portfolio.STATE_SUSPENDED,
        platform_actor=True,
    )
    with pytest.raises(ConflictError):
        transition_publication(
            portfolio=portfolio,
            target=Portfolio.STATE_UNPUBLISHED,
            platform_actor=False,
        )
    assert actor is not None


@pytest.mark.django_db
def test_every_illegal_publication_transition_raises_conflict():
    account = make_account()
    portfolio = Portfolio.all_objects.create(account=account, title="Illegal", slug="illegal")
    states = (
        Portfolio.STATE_DRAFT,
        Portfolio.STATE_PUBLISHED,
        Portfolio.STATE_UNPUBLISHED,
        Portfolio.STATE_SUSPENDED,
    )
    legal = {
        (source, target) for source, targets in LEGAL_TRANSITIONS.items() for target in targets
    }
    for source in states:
        for target in states:
            if (source, target) in legal or source == target:
                continue
            portfolio.publication_state = source
            portfolio.save(update_fields=["publication_state"])
            with pytest.raises(ConflictError):
                transition_publication(
                    portfolio=portfolio,
                    target=target,
                    platform_actor=True,
                )
