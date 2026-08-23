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
        # Paginated response envelope ({next, previous, results}), not a
        # bare list -- confirmed from the actual response shape in a real
        # test run. Check .data["results"], not len(.data) directly.
        assert len(list_resp.data["results"]) == 1


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
