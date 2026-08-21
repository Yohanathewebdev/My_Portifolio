from __future__ import annotations

from .models import AccountMembership


def accepted_membership(*, user, account=None, account_id=None):
    queryset = AccountMembership.all_objects.filter(
        user=user,
        accepted_at__isnull=False,
    )
    if account is not None:
        queryset = queryset.filter(account=account)
    if account_id is not None:
        queryset = queryset.filter(account_id=account_id)
    return queryset.select_related("account").first()
