from __future__ import annotations

from django.db import models


class PublishableMixin(models.Model):
    """Publication-state contract from design doc §12.1.

    IMPORTANT: `publication_state` must only ever be mutated through this
    app's `services.publish()` / `unpublish()` / `schedule()` functions —
    never assigned directly on the model. That discipline is what the
    design doc means by "cache correctness is a property of the system,
    not the developer" (§12.1, §16.5).

    The doc's full mixin also carries `last_published_revision (FK
    Revision)`. That field is omitted here because the `publishing` app
    (§5.1, §12.2) doesn't exist in the codebase yet — there is nowhere for
    the FK to point. Add it when `publishing.Revision` lands; nothing here
    needs to change shape to support that later.
    """

    STATE_DRAFT = "draft"
    STATE_PUBLISHED = "published"
    STATE_UNPUBLISHED = "unpublished"
    STATE_SCHEDULED = "scheduled"
    STATE_CHOICES = (
        (STATE_DRAFT, "Draft"),
        (STATE_PUBLISHED, "Published"),
        (STATE_UNPUBLISHED, "Unpublished"),
        (STATE_SCHEDULED, "Scheduled"),
    )

    publication_state = models.CharField(
        max_length=16, choices=STATE_CHOICES, default=STATE_DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
