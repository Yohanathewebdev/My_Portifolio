from typing import cast

import pytest
from rest_framework.test import APIClient

from apps.accounts.factories import AccountFactory, MembershipFactory, UserFactory
from apps.accounts.models import Account, User
from apps.profiles.models import Profile
from apps.portfolios.models import Portfolio


@pytest.mark.django_db
def test_profile_is_portfolio_scoped_sanitized_and_uses_optimistic_concurrency():
    user = cast(User, UserFactory())
    account = cast(Account, AccountFactory())
    MembershipFactory(account=account, user=user)
    portfolio = Portfolio.all_objects.create(account=account, title="One", slug="one-profile")
    client = APIClient()
    client.force_authenticate(user=user)
    url = f"/api/portfolios/{portfolio.id}/profile/"

    created = client.get(url)
    assert created.status_code == 200
    assert created.data["version"] == 1

    updated = client.patch(
        url,
        {"headline": "Developer", "biography_html": '<p onclick="x()">Hello<script>x</script></p>'},
        format="json",
        HTTP_IF_MATCH="1",
    )
    assert updated.status_code == 200
    assert updated.data["version"] == 2
    assert updated.data["biography_html"] == "<p>Hellox</p>"
    assert Profile.objects.get(portfolio=portfolio).headline == "Developer"

    stale = client.patch(url, {"headline": "Stale"}, format="json", HTTP_IF_MATCH="1")
    assert stale.status_code == 409
    assert stale.data["error"]["fields"]["current_version"] == 2
