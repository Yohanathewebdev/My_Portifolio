from __future__ import annotations

from django.http import Http404

from .models import AccountMembership
from .selectors import accepted_membership


def resolve_accounts(request):
    if not getattr(request.user, "is_authenticated", False):
        raise Http404
    return AccountMembership.all_objects.filter(
        user=request.user,
        accepted_at__isnull=False,
        account__status="active",
    ).values_list("account_id", flat=True)


def resolve_account(request):
    account_id = request.parser_context.get("kwargs", {}).get("account_id")
    if not account_id:
        raise Http404
    membership = accepted_membership(
        user=request.user,
        account_id=account_id,
    )
    if membership is None:
        raise Http404
    return membership.account


def resolve_role(request):
    account_id = request.parser_context.get("kwargs", {}).get("account_id")
    if account_id:
        membership = accepted_membership(user=request.user, account_id=account_id)
    else:
        from apps.portfolios.resolvers import resolve_portfolio

        portfolio = resolve_portfolio(request)
        membership = accepted_membership(user=request.user, account=portfolio.account)
    return membership.role if membership is not None else "anonymous"
