from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import UUID

from django.db import models, transaction

from .models import AuditLog

if TYPE_CHECKING:
    from apps.accounts.models import User


@transaction.atomic
def record_audit(
    *,
    action: str,
    target: models.Model,
    actor: models.Model | None = None,
    actor_type: str = "system",
    account_id: UUID | None = None,
    portfolio_id: UUID | None = None,
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
    ip_hash: str = "",
    correlation_id: str = "",
) -> AuditLog:
    return AuditLog.objects.create(
        actor=cast("User | None", actor),
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
