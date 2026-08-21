from typing import cast

import pytest
from rest_framework.test import APIClient

from apps.accounts.factories import AccountFactory, MembershipFactory, UserFactory
from apps.accounts.models import Account, AccountMembership, User
from apps.portfolios.models import Portfolio


def make_account() -> Account:
    return cast(Account, AccountFactory())


def make_user() -> User:
    return cast(User, UserFactory())


@pytest.mark.django_db
def test_member_of_another_account_gets_portfolio_404():
    user = make_user()
    account_a = make_account()
    account_b = make_account()
    MembershipFactory(account=account_a, user=user)
    MembershipFactory(account=account_b)
    portfolio_b = Portfolio.all_objects.create(
        account=account_b,
        title="Other",
        slug="other-portfolio",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(f"/api/portfolios/{portfolio_b.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_anonymous_requests_are_denied_but_health_is_public():
    account = make_account()
    client = APIClient()
    assert client.get(f"/api/accounts/{account.id}/").status_code in {401, 403}
    assert client.get("/healthz").status_code == 200


@pytest.mark.django_db
def test_portfolio_creation_returns_entitlement_402_after_free_limit():
    user = make_user()
    account = make_account()
    MembershipFactory(account=account, user=user)
    client = APIClient()
    client.force_authenticate(user=user)
    first = client.post(
        f"/api/accounts/{account.id}/portfolios/",
        {"title": "First", "slug": "first-api"},
        format="json",
    )
    second = client.post(
        f"/api/accounts/{account.id}/portfolios/",
        {"title": "Second", "slug": "second-api"},
        format="json",
    )
    assert first.status_code == 201
    assert second.status_code == 402
    assert second.data["error"]["fields"]["feature"] == "portfolios"


@pytest.mark.django_db
def test_account_and_membership_reads_are_scoped():
    user = make_user()
    account = make_account()
    other = make_account()
    MembershipFactory(account=account, user=user, role=AccountMembership.ROLE_OWNER)
    client = APIClient()
    client.force_authenticate(user=user)
    assert client.get(f"/api/accounts/{account.id}/").status_code == 200
    assert client.get(f"/api/accounts/{other.id}/").status_code == 404
    assert client.get(f"/api/accounts/{account.id}/members/").status_code == 200
    assert client.get(f"/api/accounts/{other.id}/members/").status_code == 404
    assert client.get("/api/me/").status_code == 200


@pytest.mark.django_db
def test_membership_invite_role_change_and_removal_are_scoped():
    user = make_user()
    account = make_account()
    other = make_account()
    MembershipFactory(account=account, user=user, role=AccountMembership.ROLE_OWNER)
    client = APIClient()
    client.force_authenticate(user=user)

    invited = client.post(
        f"/api/accounts/{account.id}/members/",
        {"email": "invited@example.com", "role": AccountMembership.ROLE_EDITOR},
        format="json",
    )
    assert invited.status_code == 201
    membership_id = invited.data["id"]
    role_changed = client.patch(
        f"/api/accounts/{account.id}/members/{membership_id}/role/",
        {"role": AccountMembership.ROLE_VIEWER},
        format="json",
    )
    assert role_changed.status_code == 200
    removed = client.delete(f"/api/accounts/{account.id}/members/{membership_id}/")
    assert removed.status_code == 204
    assert (
        client.post(
            f"/api/accounts/{other.id}/members/",
            {"email": "wrong-tenant@example.com", "role": AccountMembership.ROLE_VIEWER},
            format="json",
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_viewer_cannot_manage_members_or_delete_portfolio():
    user = make_user()
    account = make_account()
    MembershipFactory(account=account, user=user, role=AccountMembership.ROLE_VIEWER)
    portfolio = Portfolio.all_objects.create(
        account=account,
        title="Owned",
        slug="owned-portfolio",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    assert (
        client.post(
            f"/api/accounts/{account.id}/members/",
            {"email": "blocked@example.com", "role": AccountMembership.ROLE_VIEWER},
            format="json",
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/accounts/{account.id}/portfolios/{portfolio.id}/").status_code == 403
    )


@pytest.mark.django_db
def test_portfolio_patch_records_slug_history_and_delete_is_scoped():
    user = make_user()
    account = make_account()
    other = make_account()
    MembershipFactory(account=account, user=user, role=AccountMembership.ROLE_OWNER)
    portfolio = Portfolio.all_objects.create(
        account=account,
        title="Editable",
        slug="editable-portfolio",
    )
    other_portfolio = Portfolio.all_objects.create(
        account=other,
        title="Other",
        slug="other-api-portfolio",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    updated = client.patch(
        f"/api/accounts/{account.id}/portfolios/{portfolio.id}/",
        {"slug": "edited-portfolio", "title": "Updated"},
        format="json",
    )
    assert updated.status_code == 200
    assert portfolio.slug == "editable-portfolio"
    assert portfolio.slug_history.filter(old_slug="editable-portfolio").exists()
    assert (
        client.delete(f"/api/accounts/{other.id}/portfolios/{other_portfolio.id}/").status_code
        == 404
    )


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["admin", "edited-portfolio"])
def test_invalid_portfolio_slugs_return_400(slug):
    user = make_user()
    account = make_account()
    MembershipFactory(account=account, user=user, role=AccountMembership.ROLE_OWNER)
    portfolio = Portfolio.all_objects.create(
        account=account,
        title="Existing",
        slug="edited-portfolio",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/accounts/{account.id}/portfolios/",
        {"title": "Invalid", "slug": slug},
        format="json",
    )
    assert response.status_code == 400
    assert "slug" in response.data["error"]["fields"]
    assert portfolio.slug == "edited-portfolio"
