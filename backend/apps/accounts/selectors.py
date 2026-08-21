from __future__ import annotations

from .models import AccountMembership


def accepted_membership(*, user, account):
    return AccountMembership.all_objects.filter(
        user=user,
        account=account,
        accepted_at__isnull=False,
    ).first()
