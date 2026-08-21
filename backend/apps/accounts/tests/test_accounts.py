from typing import cast

import pytest
from django.db import IntegrityError

from apps.accounts.factories import AccountFactory, MembershipFactory, UserFactory
from apps.accounts.models import AccountMembership
from apps.accounts.services import invite_member, signup, transfer_ownership
from apps.core.audit import AuditLog


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
    assert AuditLog.objects.filter(action="signup").exists()
    assert AuditLog.objects.filter(action="portfolio_created").exists()
    assert AuditLog.objects.filter(action="subscription_created").exists()


@pytest.mark.django_db
def test_invited_user_has_unusable_password_and_ownership_can_transfer():
    account = AccountFactory()
    owner = UserFactory()
    replacement_user = UserFactory()
    current = cast(
        AccountMembership,
        MembershipFactory(
            account=account,
            user=owner,
            role=AccountMembership.ROLE_OWNER,
        ),
    )
    replacement = cast(
        AccountMembership,
        MembershipFactory(
            account=account,
            user=replacement_user,
            role=AccountMembership.ROLE_EDITOR,
        ),
    )
    invited = invite_member(
        account=account,
        inviter=owner,
        email="new-invite@example.com",
        role=AccountMembership.ROLE_VIEWER,
    )
    assert not invited.user.has_usable_password()
    transfer_ownership(membership=current, new_owner=replacement, actor=owner)
    current.refresh_from_db()
    replacement.refresh_from_db()
    assert current.role == AccountMembership.ROLE_ADMIN
    assert replacement.role == AccountMembership.ROLE_OWNER
    assert AuditLog.objects.filter(action="membership_invited").exists()
    assert AuditLog.objects.filter(action="ownership_transferred").exists()
