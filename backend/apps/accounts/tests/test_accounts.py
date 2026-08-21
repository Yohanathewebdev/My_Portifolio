import pytest
from django.db import IntegrityError

from apps.accounts.factories import AccountFactory, MembershipFactory, UserFactory
from apps.accounts.models import AccountMembership
from apps.accounts.services import signup


@pytest.mark.django_db
def test_owner_constraint_is_database_enforced():
    account = AccountFactory()
    first = MembershipFactory(account=account, role=AccountMembership.ROLE_OWNER)
    with pytest.raises(IntegrityError):
        MembershipFactory(
            account=account,
            user=UserFactory(),
            role=AccountMembership.ROLE_OWNER,
        )
    assert first.role == AccountMembership.ROLE_OWNER


@pytest.mark.django_db
def test_signup_provisions_free_active_subscription_and_audit():
    user, account, membership, portfolio, subscription = signup(
        email="signup@example.com",
        password="Password123!",
        account_name="Signup account",
        account_slug="signup-account",
        portfolio_title="First portfolio",
        portfolio_slug="signup-portfolio",
    )
    assert user.email == "signup@example.com"
    assert membership.accepted_at is not None
    assert portfolio.account_id == account.id
    assert subscription.plan_id
    assert not subscription.provider_customer_id
    assert not subscription.provider_subscription_id
