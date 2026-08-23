from __future__ import annotations

import pytest

from apps.core.managers import UnscopedQueryError
from apps.projects.models import Project, Tag

# NOTE: fixtures `portfolio_a`, `portfolio_b`, `user_a`, `user_b` are
# assumed to come from the shared conftest per Â§27.7 ("two accounts by
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

