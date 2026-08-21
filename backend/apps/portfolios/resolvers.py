from __future__ import annotations

from django.http import Http404

from apps.accounts.selectors import accepted_membership

from .models import Portfolio


def resolve_portfolio(request):
    parser_context = getattr(request, "parser_context", {})
    identifier = parser_context.get("kwargs", {})
    identifier = (
        identifier.get("portfolio_id") or identifier.get("pk") or identifier.get("portfolio_slug")
    )
    if not identifier:
        raise Http404
    try:
        portfolio = (
            Portfolio.all_objects.get(pk=identifier)
            if len(str(identifier)) == 36
            else Portfolio.all_objects.get(slug=identifier)
        )
    except (Portfolio.DoesNotExist, ValueError):
        raise Http404 from None
    if accepted_membership(user=request.user, account=portfolio.account) is None:
        raise Http404
    return portfolio
