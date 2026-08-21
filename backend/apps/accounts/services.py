from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.billing.models import Subscription
from apps.billing.services import free_plan
from apps.core.audit import record_audit
from apps.core.exceptions import ConflictError
from apps.core.slug_registry import validate_reserved_slug

from .models import Account, AccountMembership, User
from .passwords import validate_password_not_breached

if TYPE_CHECKING:
    from apps.portfolios.models import Portfolio


@transaction.atomic
def signup(
    *,
    email: str,
    password: str,
    account_name: str,
    account_slug: str,
    portfolio_title: str,
    portfolio_slug: str,
    billing_email: str | None = None,
    country_code: str = "",
) -> tuple[User, Account, AccountMembership, Portfolio, Subscription]:
    try:
        validate_reserved_slug(account_slug)
    except ValueError as exc:
        raise ValidationError({"account_slug": [str(exc)]}) from exc
    validate_password_not_breached(password)
    user = User.objects.create_user(email=email, password=password)
    account = Account.all_objects.create(
        name=account_name,
        slug=account_slug,
        billing_email=billing_email or email,
        country_code=country_code,
        plan_ref="free",
    )
    membership = AccountMembership.all_objects.create(
        account=account,
        user=user,
        role=AccountMembership.ROLE_OWNER,
        accepted_at=timezone.now(),
    )
    from apps.portfolios.services import create_portfolio

    portfolio = create_portfolio(
        account=account,
        title=portfolio_title,
        slug=portfolio_slug,
        actor=user,
    )
    plan = free_plan()
    subscription = Subscription.objects.create(
        account=account,
        plan=plan,
        status=Subscription.STATUS_ACTIVE,
    )
    record_audit(
        action="subscription_created",
        target=subscription,
        actor=user,
        account_id=account.id,
        after={"plan": "free", "status": "active"},
    )
    record_audit(
        action="signup",
        target=account,
        actor=user,
        account_id=account.id,
        after={"portfolio_id": str(portfolio.id)},
    )
    return user, account, membership, portfolio, subscription


@transaction.atomic
def invite_member(*, account, inviter, email: str, role: str):
    normalized_email = User.objects.normalize_email(email)
    user = User.objects.filter(email=normalized_email).first()
    if user is None:
        user = User.objects.create_user(email=normalized_email)
    membership = AccountMembership.all_objects.create(
        account=account,
        user=user,
        role=role,
        invited_by=inviter,
        invited_at=timezone.now(),
    )
    record_audit(
        action="membership_invited",
        target=membership,
        actor=inviter,
        account_id=account.id,
        after={"user_id": str(user.id), "role": role},
    )
    return membership


@transaction.atomic
def change_member_role(*, membership: AccountMembership, role: str, actor=None):
    if membership.role == AccountMembership.ROLE_OWNER and role != AccountMembership.ROLE_OWNER:
        raise ConflictError("An account must retain its owner.")
    previous_role = membership.role
    membership.role = role
    membership.save(update_fields=["role", "updated_at"])
    record_audit(
        action="membership_role_changed",
        target=membership,
        actor=actor,
        account_id=membership.account_id,
        after={"user_id": str(membership.user_id), "before_role": previous_role, "role": role},
    )
    return membership


@transaction.atomic
def remove_member(*, membership: AccountMembership, actor=None):
    if membership.role == AccountMembership.ROLE_OWNER:
        raise ConflictError("An account must retain its owner.")
    record_audit(
        action="membership_removed",
        target=membership,
        actor=actor,
        account_id=membership.account_id,
        before={"user_id": str(membership.user_id), "role": membership.role},
    )
    membership.delete()


@transaction.atomic
def transfer_ownership(
    *, membership: AccountMembership, new_owner: AccountMembership, actor=None
) -> tuple[AccountMembership, AccountMembership]:
    if membership.role != AccountMembership.ROLE_OWNER:
        raise ConflictError("The current membership is not the account owner.")
    if new_owner.account_id != membership.account_id:
        raise ConflictError("Ownership can only transfer within one account.")
    if new_owner.pk == membership.pk:
        raise ConflictError("Ownership must transfer to another member.")
    current = AccountMembership.all_objects.select_for_update().get(pk=membership.pk)
    replacement = AccountMembership.all_objects.select_for_update().get(pk=new_owner.pk)
    if replacement.role == AccountMembership.ROLE_OWNER:
        raise ConflictError("The replacement member is already an owner.")
    current.role = AccountMembership.ROLE_ADMIN
    current.save(update_fields=["role", "updated_at"])
    replacement.role = AccountMembership.ROLE_OWNER
    replacement.save(update_fields=["role", "updated_at"])
    record_audit(
        action="ownership_transferred",
        target=current.account,
        actor=actor,
        account_id=current.account_id,
        before={"owner_id": str(current.user_id)},
        after={"owner_id": str(replacement.user_id)},
    )
    return current, replacement
