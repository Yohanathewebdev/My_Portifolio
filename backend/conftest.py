from __future__ import annotations

import pytest
from django.utils import timezone

from apps.accounts.models import Account, AccountMembership, User
from apps.portfolios.models import Portfolio

# No shared fixtures existed anywhere in the project before this file —
# confirmed via `Get-ChildItem -Recurse -Filter conftest.py` returning
# nothing. This provides the "two accounts by default" pattern the design
# doc's §27.7 describes, used by apps/projects/tests/*.

# NOTE: Account/AccountMembership/Portfolio all use scoped managers as
# `.objects` (AccountScopedManager / PrimaryAccountScopedManager), which
# raise UnscopedQueryError unconditionally until you call `.for_accounts()`
# — so fixtures create through `.all_objects` (the plain, unscoped
# manager) instead. This is the correct, intentional bypass — the same
# one `create_for_portfolio()` uses internally for portfolio-owned models.


@pytest.fixture
def user_a(db):
    return User.objects.create_user(email="user-a@example.com", password="testpass123")


@pytest.fixture
def user_b(db):
    return User.objects.create_user(email="user-b@example.com", password="testpass123")


@pytest.fixture
def account_a(db, user_a):
    account = Account.all_objects.create(
        name="Account A",
        slug="account-a",
        billing_email="user-a@example.com",
    )
    # accepted_at is required, not just membership existing -- confirmed by
    # apps.billing.entitlements.measure_team_members(), which filters
    # AccountMembership on accepted_at__isnull=False. Without this, a
    # scoped resolver that follows the same convention (e.g. whatever
    # settings.ACCOUNT_RESOLVER does) will treat the membership as
    # pending/inactive and return zero accounts for this user.
    AccountMembership.all_objects.create(
        account=account,
        user=user_a,
        role=AccountMembership.ROLE_OWNER,
        accepted_at=timezone.now(),
    )
    return account


@pytest.fixture
def account_b(db, user_b):
    account = Account.all_objects.create(
        name="Account B",
        slug="account-b",
        billing_email="user-b@example.com",
    )
    AccountMembership.all_objects.create(
        account=account,
        user=user_b,
        role=AccountMembership.ROLE_OWNER,
        accepted_at=timezone.now(),
    )
    return account


@pytest.fixture
def portfolio_a(db, account_a):
    return Portfolio.all_objects.create(account=account_a, slug="portfolio-a", title="Portfolio A")


@pytest.fixture
def portfolio_b(db, account_b):
    return Portfolio.all_objects.create(account=account_b, slug="portfolio-b", title="Portfolio B")
