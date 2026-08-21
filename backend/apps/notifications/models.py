from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class EmailMessage(BaseModel):
    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_QUEUED, "Queued"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    )

    to_email = models.EmailField()
    template_code = models.CharField(max_length=100)
    context = models.JSONField(default=dict)
    provider_message_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    error = models.TextField(blank=True)
    related_object_ref = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template_code", "related_object_ref", "to_email"],
                name="unique_email_message_idempotency",
            )
        ]
