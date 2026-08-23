from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.content.models import MediaAsset
from apps.core.models import BaseModel, PortfolioOwnedModel
from apps.core.sanitization import sanitize_html


class Tag(BaseModel):
    """Portfolio-scoped tag for projects.

    Design doc Â§11 also wants a Tag for `blog`, portfolio-scoped the same
    way. Since `blog` doesn't exist yet, Tag lives here rather than in a
    speculative shared taxonomy app. When `blog` is built, either point it
    at this model or extract a shared one â€” don't fork a second Tag model.
    """

    portfolio = models.ForeignKey(
        "portfolios.Portfolio", on_delete=models.CASCADE, related_name="project_tags"
    )
    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=70)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "slug"], name="unique_project_tag_slug")
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:70]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Project(PortfolioOwnedModel):
    """Design doc Â§10, rebuilt to match apps.content's Article â€” the real,
    working precedent for portfolio-scoped + publishable content in this
    codebase (confirmed from content/models.py, content/views.py).

    Deliberate deviations from Article, each flagged:

    1. `cover_image` is a real FK to `apps.content.MediaAsset` â€” media
       already exists (inside `content`, not a separate `media` app as
       the design doc implies). No gallery/ProjectImage yet; nothing to
       build it against until that's actually needed.
    2. `clean()` enforces that `cover_image.portfolio == self.portfolio`,
       and `save()` calls `self.clean()` before writing. Article's save()
       doesn't call clean() at all. Added here because an unscoped
       MediaAsset queryset in the serializer (see serializers.py) means
       nothing else stops a cross-portfolio MediaAsset from being
       attached â€” this is the same class of bug as SEC-8, so it's worth
       the inconsistency with Article's simpler save().
    3. `publish()`/`unpublish()` call `apps.core.audit.record_audit()`.
       Article.publish() does not. Design doc Â§24.6 requires publish
       actions to be audited; if that's handled elsewhere for Article
       (a signal on status change, maybe), this becomes redundant here â€”
       worth checking rather than assuming either app is "right".
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

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    description = models.TextField(blank=True)  # sanitized HTML, Â§24.4
    description_editor_json = models.JSONField(default=dict, blank=True)
    summary = models.CharField(max_length=300, blank=True)
    client = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    cover_image = models.ForeignKey(
        MediaAsset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="project_covers",
    )

    tags = models.ManyToManyField(Tag, blank=True, related_name="projects")
    links = models.JSONField(default=list, blank=True)  # [{label, url}]
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    publication_state = models.CharField(
        max_length=16, choices=STATE_CHOICES, default=STATE_DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)

    version = models.PositiveIntegerField(default=1)  # OCC lock, matches Article

    class Meta:
        ordering = ["-published_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["portfolio", "slug"], name="unique_project_slug")
        ]
        indexes = [
            models.Index(fields=["portfolio", "publication_state", "-published_at"]),
        ]

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "end_date must be on or after start_date"})
        for link in self.links:
            if not isinstance(link, dict) or "url" not in link:
                raise ValidationError({"links": "each link requires a url"})
        if self.cover_image_id and self.cover_image.portfolio_id != self.portfolio_id:
            raise ValidationError(
                {"cover_image": "cover image must belong to the same portfolio as the project"}
            )

    def save(self, *args, **kwargs):
        if self.description:
            self.description = sanitize_html(self.description)
        if not self.slug:
            self.slug = slugify(self.title)
        self.clean()
        super().save(*args, **kwargs)

    def publish(self, *, actor=None):
        """Mirrors Article.publish()'s shape. Unlike Article, writes an
        AuditLog entry (see class docstring, point 3) and accepts an
        optional `actor` â€” Article's caller (ArticleViewSet.publish) never
        passes one, so audit there would show actor_type="system" too if
        it existed at all. Pass request.user from the view here."""
        from apps.core.audit import record_audit

        before_state = self.publication_state
        self.publication_state = self.STATE_PUBLISHED
        self.published_at = timezone.now()
        self.save()
        record_audit(
            action="project.publish",
            target=self,
            actor=actor,
            actor_type="user" if actor else "system",
            account_id=self.portfolio.account_id,
            portfolio_id=self.portfolio_id,
            before={"publication_state": before_state},
            after={"publication_state": self.publication_state},
        )

    def unpublish(self, *, actor=None):
        from apps.core.audit import record_audit

        before_state = self.publication_state
        self.publication_state = self.STATE_UNPUBLISHED
        self.save()
        record_audit(
            action="project.unpublish",
            target=self,
            actor=actor,
            actor_type="user" if actor else "system",
            account_id=self.portfolio.account_id,
            portfolio_id=self.portfolio_id,
            before={"publication_state": before_state},
            after={"publication_state": self.publication_state},
        )

    def __str__(self) -> str:
        return self.title

