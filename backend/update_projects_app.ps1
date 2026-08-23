# Delta update -- overwrites the 5 files that changed after seeing
# apps/content/views.py and apps/content/models.py. Run from your
# backend project root (same folder as manage.py). Safe to re-run.

Write-Host "Updating apps/projects/ with corrected files..."

@'
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

    Design doc §11 also wants a Tag for `blog`, portfolio-scoped the same
    way. Since `blog` doesn't exist yet, Tag lives here rather than in a
    speculative shared taxonomy app. When `blog` is built, either point it
    at this model or extract a shared one — don't fork a second Tag model.
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
    """Design doc §10, rebuilt to match apps.content's Article — the real,
    working precedent for portfolio-scoped + publishable content in this
    codebase (confirmed from content/models.py, content/views.py).

    Deliberate deviations from Article, each flagged:

    1. `cover_image` is a real FK to `apps.content.MediaAsset` — media
       already exists (inside `content`, not a separate `media` app as
       the design doc implies). No gallery/ProjectImage yet; nothing to
       build it against until that's actually needed.
    2. `clean()` enforces that `cover_image.portfolio == self.portfolio`,
       and `save()` calls `self.clean()` before writing. Article's save()
       doesn't call clean() at all. Added here because an unscoped
       MediaAsset queryset in the serializer (see serializers.py) means
       nothing else stops a cross-portfolio MediaAsset from being
       attached — this is the same class of bug as SEC-8, so it's worth
       the inconsistency with Article's simpler save().
    3. `publish()`/`unpublish()` call `apps.core.audit.record_audit()`.
       Article.publish() does not. Design doc §24.6 requires publish
       actions to be audited; if that's handled elsewhere for Article
       (a signal on status change, maybe), this becomes redundant here —
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
    description = models.TextField(blank=True)  # sanitized HTML, §24.4
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
        optional `actor` — Article's caller (ArticleViewSet.publish) never
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

'@ | Set-Content -Path apps\projects\models.py -Encoding UTF8
Write-Host "  wrote apps\projects\models.py"

@'
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import MediaAsset

from .models import Project, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]
        read_only_fields = ["id", "slug"]


class ProjectSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(slug_field="name", many=True, read_only=True)
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=60),
        write_only=True,
        required=False,
        help_text="Tag names; tags are get-or-created per portfolio.",
    )

    # NOTE: queryset is MediaAsset.all_objects (the unscoped manager), not
    # MediaAsset.objects (PortfolioScopedManager) — the latter would raise
    # UnscopedQueryError immediately, since a serializer field's queryset
    # is built with no portfolio in scope. That means this field alone
    # does NOT prevent attaching another portfolio's MediaAsset — that
    # check lives in Project.clean() instead (see models.py). Don't remove
    # the model-level check on the assumption this field already covers it.
    cover_image = serializers.PrimaryKeyRelatedField(
        queryset=MediaAsset.all_objects.all(), required=False, allow_null=True
    )

    # Exposed read-only so clients can send it back as If-Match / body
    # `version` on update, per ContentViewSet.update()'s OCC check.
    version = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "description_editor_json",
            "summary",
            "client",
            "role",
            "start_date",
            "end_date",
            "cover_image",
            "tags",
            "tag_names",
            "links",
            "is_featured",
            "sort_order",
            "publication_state",
            "published_at",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "publication_state",
            "published_at",
            "version",
            "created_at",
            "updated_at",
        ]

    def validate_links(self, value):
        for link in value:
            if not isinstance(link, dict) or "url" not in link:
                raise serializers.ValidationError("each link requires a 'url' key")
        return value

'@ | Set-Content -Path apps\projects\serializers.py -Encoding UTF8
Write-Host "  wrote apps\projects\serializers.py"

@'
from __future__ import annotations

from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import ConflictError
from apps.core.permissions import CreateEditPermission
from apps.core.views import AccountScopedViewSet

from .models import Project, Tag
from .serializers import ProjectSerializer

# This duplicates ~40 lines of apps.content.views.ContentViewSet
# (get_portfolio, the OCC-aware update(), get_queryset) rather than
# importing that class directly. Reasoning: ContentViewSet lives in the
# `content` app, and having `projects` import view internals from an
# unrelated content-type app would be a real coupling, not a convenience
# — the design doc's app boundaries (§5.1) treat these as separate
# domains. If a third app needs this same shape, that's the point to
# extract a shared base into apps.core.views — not before.
#
# permission_classes = [CreateEditPermission] applied uniformly to every
# action (including list/retrieve) mirrors ContentViewSet exactly. Note
# this means viewer-role users can't even read drafts through this
# endpoint, despite ROLE_MATRIX having a distinct "read_draft" row that
# permits it. That's true of ArticleViewSet too, as shown — not something
# introduced here. Worth deciding deliberately whether that's intended
# platform-wide, rather than each new app quietly inheriting the gap.


class ProjectViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    AccountScopedViewSet,
):
    serializer_class = ProjectSerializer
    permission_classes = [CreateEditPermission]
    queryset = Project

    def get_portfolio(self):
        from apps.portfolios.models import Portfolio

        return Portfolio.objects.for_accounts(self.get_accounts()).get(
            pk=self.kwargs["portfolio_id"]
        )

    def get_queryset(self):
        return self.queryset.objects.for_portfolio(self.get_portfolio())

    def perform_create(self, serializer):
        model = self.get_serializer_class().Meta.model
        tag_names = serializer.validated_data.pop("tag_names", [])
        portfolio = self.get_portfolio()
        project = model.objects.create_for_portfolio(
            portfolio, **serializer.validated_data
        )
        if tag_names:
            _attach_tags(project, portfolio, tag_names)
        serializer.instance = project

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if hasattr(instance, "version"):
            expected = request.headers.get("If-Match") or request.data.get("version")
            if expected is None or int(expected) != instance.version:
                raise ConflictError(
                    current_version=instance.version, expected_version=int(expected or 0)
                )

        tag_names = request.data.get("tag_names")
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("tag_names", None)

        if hasattr(instance, "version"):
            serializer.save(version=instance.version + 1)
        else:
            serializer.save()

        if tag_names is not None:
            _attach_tags(instance, self.get_portfolio(), tag_names, replace=True)

        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        """Mirrors ArticleViewSet.publish() exactly, including the
        already-published 400 guard."""
        project = self.get_object()
        if project.publication_state == Project.STATE_PUBLISHED:
            return Response(
                {"detail": "Project is already published."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project.publish(actor=request.user)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def unpublish(self, request, *args, **kwargs):
        project = self.get_object()
        project.unpublish(actor=request.user)
        return Response(self.get_serializer(project).data)


def _attach_tags(project, portfolio, names, *, replace=False):
    tags = []
    for name in names:
        slug = name.strip().lower().replace(" ", "-")[:70]
        tag, _ = Tag.objects.get_or_create(
            portfolio=portfolio, slug=slug, defaults={"name": name.strip()}
        )
        tags.append(tag)
    if replace:
        project.tags.set(tags)
    else:
        project.tags.add(*tags)

'@ | Set-Content -Path apps\projects\views.py -Encoding UTF8
Write-Host "  wrote apps\projects\views.py"

@'
from __future__ import annotations

import pytest

from apps.core.managers import UnscopedQueryError
from apps.projects.models import Project, Tag

# NOTE: fixtures `portfolio_a`, `portfolio_b`, `user_a`, `user_b` are
# assumed to come from the shared conftest per §27.7 ("two accounts by
# default"). Adjust names to whatever your real conftest provides.


@pytest.mark.django_db
def test_default_manager_raises_without_scope():
    """SEC-8: an unscoped query on a PortfolioOwnedModel must fail loud."""
    with pytest.raises(UnscopedQueryError):
        list(Project.objects.all())


@pytest.mark.django_db
def test_cross_tenant_isolation(portfolio_a, portfolio_b):
    Project.objects.create_for_portfolio(portfolio_a, title="A's project", slug="a-project")
    assert Project.objects.for_portfolio(portfolio_a).count() == 1
    assert Project.objects.for_portfolio(portfolio_b).count() == 0


@pytest.mark.django_db
def test_slug_unique_per_portfolio(portfolio_a):
    Project.objects.create_for_portfolio(portfolio_a, title="X", slug="dup")
    with pytest.raises(Exception):
        Project.objects.create_for_portfolio(portfolio_a, title="X2", slug="dup")


@pytest.mark.django_db
def test_same_slug_allowed_across_portfolios(portfolio_a, portfolio_b):
    Project.objects.create_for_portfolio(portfolio_a, title="X", slug="same")
    Project.objects.create_for_portfolio(portfolio_b, title="Y", slug="same")
    assert Project.objects.for_portfolio(portfolio_a).count() == 1
    assert Project.objects.for_portfolio(portfolio_b).count() == 1


@pytest.mark.django_db
def test_publish_sets_state_and_timestamp(portfolio_a, user_a):
    project = Project.objects.create_for_portfolio(portfolio_a, title="X", slug="x")
    assert project.publication_state == Project.STATE_DRAFT
    assert project.published_at is None

    project.publish(actor=user_a)
    project.refresh_from_db()
    assert project.publication_state == Project.STATE_PUBLISHED
    assert project.published_at is not None


@pytest.mark.django_db
def test_unpublish_after_publish(portfolio_a, user_a):
    project = Project.objects.create_for_portfolio(portfolio_a, title="X", slug="x")
    project.publish(actor=user_a)
    project.unpublish(actor=user_a)
    project.refresh_from_db()
    assert project.publication_state == Project.STATE_UNPUBLISHED


@pytest.mark.django_db
def test_publish_writes_audit_log(portfolio_a, user_a):
    from apps.core.models import AuditLog

    project = Project.objects.create_for_portfolio(portfolio_a, title="X", slug="x")
    project.publish(actor=user_a)

    entries = AuditLog.objects.filter(target_type="projects.project", target_id=str(project.id))
    actions = set(entries.values_list("action", flat=True))
    assert "project.publish" in actions

    entry = entries.get(action="project.publish")
    assert entry.actor_id == user_a.id
    assert entry.actor_type == "user"


@pytest.mark.django_db
def test_end_date_before_start_date_rejected(portfolio_a):
    with pytest.raises(Exception):
        Project.objects.create_for_portfolio(
            portfolio_a,
            title="X",
            slug="x",
            start_date="2026-06-01",
            end_date="2026-01-01",
        )


@pytest.mark.django_db
def test_delete_is_soft(portfolio_a):
    project = Project.objects.create_for_portfolio(portfolio_a, title="X", slug="x")
    project.delete()

    assert Project.objects.for_portfolio(portfolio_a).count() == 0
    assert Project.all_objects.filter(pk=project.id, is_deleted=True).exists()


@pytest.mark.django_db
def test_tags_are_scoped_per_portfolio(portfolio_a, portfolio_b):
    """Same tag name on two portfolios must create two Tag rows, not share one."""
    Tag.objects.create(portfolio=portfolio_a, name="Branding")
    Tag.objects.create(portfolio=portfolio_b, name="Branding")
    assert Tag.objects.filter(name="Branding").count() == 2


@pytest.mark.django_db
def test_cover_image_from_other_portfolio_rejected(portfolio_a, portfolio_b):
    """SEC-8-class check: cover_image must belong to the same portfolio
    as the project. See Project.clean() in models.py."""
    from apps.content.models import MediaAsset

    other_asset = MediaAsset.objects.create_for_portfolio(
        portfolio_b,
        file_key="x.jpg",
        file_name="x.jpg",
        file_size=100,
        mime_type="image/jpeg",
    )
    with pytest.raises(Exception):
        Project.objects.create_for_portfolio(
            portfolio_a, title="X", slug="x", cover_image=other_asset
        )


@pytest.mark.django_db
def test_version_defaults_to_one_and_is_not_auto_incremented(portfolio_a):
    """version is only ever bumped by ProjectViewSet.update() explicitly
    passing version=instance.version + 1 into serializer.save() -- it is
    NOT incremented by Project.save() itself. A plain model-level save()
    (as used here) must leave it unchanged, matching ContentViewSet's
    OCC pattern exactly."""
    project = Project.objects.create_for_portfolio(portfolio_a, title="X", slug="x")
    assert project.version == 1
    project.title = "Updated"
    project.save()
    project.refresh_from_db()
    assert project.version == 1

'@ | Set-Content -Path apps\projects\tests\test_models.py -Encoding UTF8
Write-Host "  wrote apps\projects\tests\test_models.py"

@'
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

# `api_client_as(user)` equivalent: force_authenticate is a placeholder —
# swap for your real auth helper if tests need real JWTs end-to-end.


@pytest.mark.django_db
class TestProjectCrossTenantMatrix:
    """§27.4: User A's token against Portfolio B must 403/404, never 200."""

    def test_list_wrong_portfolio_denied(self, portfolio_b, user_a):
        client = APIClient()
        client.force_authenticate(user=user_a)
        resp = client.get(f"/api/portfolios/{portfolio_b.id}/projects/")
        assert resp.status_code in (403, 404)

    def test_create_wrong_portfolio_denied(self, portfolio_b, user_a):
        client = APIClient()
        client.force_authenticate(user=user_a)
        resp = client.post(
            f"/api/portfolios/{portfolio_b.id}/projects/",
            {"title": "Injected", "slug": "injected"},
            format="json",
        )
        assert resp.status_code in (403, 404)

    def test_publish_wrong_portfolio_denied(self, portfolio_b, user_a, user_b):
        from apps.projects.models import Project

        project = Project.objects.create_for_portfolio(portfolio_b, title="X", slug="x")
        client = APIClient()
        client.force_authenticate(user=user_a)
        resp = client.post(f"/api/portfolios/{portfolio_b.id}/projects/{project.id}/publish/")
        assert resp.status_code in (403, 404)


@pytest.mark.django_db
class TestProjectHappyPath:
    def test_create_publish_list(self, portfolio_a, user_a):
        client = APIClient()
        client.force_authenticate(user=user_a)

        create_resp = client.post(
            f"/api/portfolios/{portfolio_a.id}/projects/",
            {"title": "New Site", "slug": "new-site", "tag_names": ["Web", "Design"]},
            format="json",
        )
        assert create_resp.status_code == 201
        project_id = create_resp.data["id"]
        assert create_resp.data["publication_state"] == "draft"
        assert create_resp.data["version"] == 1

        publish_resp = client.post(
            f"/api/portfolios/{portfolio_a.id}/projects/{project_id}/publish/"
        )
        assert publish_resp.status_code == 200
        assert publish_resp.data["publication_state"] == "published"

        already_published = client.post(
            f"/api/portfolios/{portfolio_a.id}/projects/{project_id}/publish/"
        )
        assert already_published.status_code == 400

        list_resp = client.get(f"/api/portfolios/{portfolio_a.id}/projects/")
        assert list_resp.status_code == 200
        assert len(list_resp.data) == 1


@pytest.mark.django_db
class TestProjectOptimisticConcurrency:
    """Matches ContentViewSet.update()'s If-Match / body-version check."""

    def test_update_without_version_returns_409(self, portfolio_a, user_a):
        from apps.projects.models import Project

        project = Project.objects.create_for_portfolio(portfolio_a, title="X", slug="x")
        client = APIClient()
        client.force_authenticate(user=user_a)

        resp = client.patch(
            f"/api/portfolios/{portfolio_a.id}/projects/{project.id}/",
            {"title": "New title"},
            format="json",
        )
        assert resp.status_code == 409

    def test_update_with_correct_version_succeeds_and_bumps_version(self, portfolio_a, user_a):
        from apps.projects.models import Project

        project = Project.objects.create_for_portfolio(portfolio_a, title="X", slug="x")
        client = APIClient()
        client.force_authenticate(user=user_a)

        resp = client.patch(
            f"/api/portfolios/{portfolio_a.id}/projects/{project.id}/",
            {"title": "New title", "version": 1},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["version"] == 2

    def test_update_with_stale_version_returns_409(self, portfolio_a, user_a):
        from apps.projects.models import Project

        project = Project.objects.create_for_portfolio(portfolio_a, title="X", slug="x")
        client = APIClient()
        client.force_authenticate(user=user_a)

        # First update succeeds, bumping version to 2.
        client.patch(
            f"/api/portfolios/{portfolio_a.id}/projects/{project.id}/",
            {"title": "First edit", "version": 1},
            format="json",
        )
        # Second update replays the now-stale version=1.
        resp = client.patch(
            f"/api/portfolios/{portfolio_a.id}/projects/{project.id}/",
            {"title": "Conflicting edit", "version": 1},
            format="json",
        )
        assert resp.status_code == 409

'@ | Set-Content -Path apps\projects\tests\test_api.py -Encoding UTF8
Write-Host "  wrote apps\projects\tests\test_api.py"

# Deprecate the old services/selectors layer (renamed, not deleted)
if (Test-Path apps\projects\services.py) {
    Rename-Item apps\projects\services.py services.py.DEPRECATED -Force
    Write-Host "  renamed services.py -> services.py.DEPRECATED"
}
if (Test-Path apps\projects\selectors.py) {
    Rename-Item apps\projects\selectors.py selectors.py.DEPRECATED -Force
    Write-Host "  renamed selectors.py -> selectors.py.DEPRECATED"
}

Write-Host ""
Write-Host "Done. Read INTEGRATION_v2.md before running makemigrations --"
Write-Host "the model shape changed (new cover_image FK, new version field)."