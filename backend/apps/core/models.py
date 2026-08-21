import uuid
from typing import ClassVar

from django.conf import settings
from django.db import models

from .managers import PortfolioScopedManager, SoftDeleteManager


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(BaseModel):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects: ClassVar[SoftDeleteManager] = SoftDeleteManager()
    all_objects: ClassVar[models.Manager["SoftDeleteModel"]] = models.Manager()  # type: ignore[no-redef]

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"], using=using)


class PortfolioOwnedModel(SoftDeleteModel):
    portfolio = models.ForeignKey(
        "portfolios.Portfolio",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
    )
    objects: ClassVar[PortfolioScopedManager] = PortfolioScopedManager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"
        default_manager_name = "objects"
        indexes = [models.Index(fields=["portfolio", "-created_at"])]


class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    actor_type = models.CharField(max_length=32)
    account_id = models.UUIDField(null=True, blank=True)
    portfolio_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    ip_hash = models.CharField(max_length=128, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action}:{self.target_type}:{self.target_id}"
