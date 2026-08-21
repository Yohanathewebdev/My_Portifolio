from __future__ import annotations

from .models import Portfolio


def portfolio_for_account(*, account, portfolio_id):
    return Portfolio.all_objects.filter(account=account, pk=portfolio_id).first()
