from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.billing.entitlements import check_and_consume
from apps.billing.models import Subscription
from apps.billing.services import free_plan
from apps.core.audit import record_audit
from apps.core.exceptions import ConflictError

from .models import Account, AccountMembership, User

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
    from apps.portfolios.models import Portfolio

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
    check_and_consume(account, "portfolios")
    portfolio = Portfolio.all_objects.create(
        account=account,
        title=portfolio_title,
        slug=portfolio_slug,
    )
    plan = free_plan()
    subscription = Subscription.objects.create(
        account=account,
        plan=plan,
        status=Subscription.STATUS_ACTIVE,
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
    user, _ = User.objects.get_or_create(email=User.objects.normalize_email(email))
    return AccountMembership.all_objects.create(
        account=account,
        user=user,
        role=role,
        invited_by=inviter,
        invited_at=timezone.now(),
    )


@transaction.atomic
def change_member_role(*, membership: AccountMembership, role: str):
    if membership.role == AccountMembership.ROLE_OWNER and role != AccountMembership.ROLE_OWNER:
        raise ConflictError("An account must retain its owner.")
    membership.role = role
    membership.save(update_fields=["role", "updated_at"])
    return membership


@transaction.atomic
def remove_member(*, membership: AccountMembership):
    if membership.role == AccountMembership.ROLE_OWNER:
        raise ConflictError("An account must retain its owner.")
    membership.delete()
