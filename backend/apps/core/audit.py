from __future__ import annotations

from typing import Any

from django.db import transaction

from .models import AuditLog


@transaction.atomic
def record_audit(
    *,
    action: str,
    target: Any,
    actor: Any = None,
    actor_type: str = "system",
    account_id: Any = None,
    portfolio_id: Any = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip_hash: str = "",
    correlation_id: str = "",
) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor,
        actor_type=actor_type,
        account_id=account_id,
        portfolio_id=portfolio_id,
        action=action,
        target_type=f"{target._meta.app_label}.{target._meta.model_name}",
        target_id=str(target.pk),
        before=before,
        after=after,
        ip_hash=ip_hash,
        correlation_id=correlation_id,
    )
