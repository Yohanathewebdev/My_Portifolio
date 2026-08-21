from __future__ import annotations

from django.http import Http404

from .models import AccountMembership


def resolve_accounts(request):
    if not getattr(request.user, "is_authenticated", False):
        raise Http404
    return AccountMembership.all_objects.filter(
        user=request.user,
        accepted_at__isnull=False,
        account__status="active",
    ).values_list("account_id", flat=True)
