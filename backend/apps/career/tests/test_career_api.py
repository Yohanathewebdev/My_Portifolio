from typing import cast

import pytest
from rest_framework.test import APIClient

from apps.accounts.factories import AccountFactory, MembershipFactory, UserFactory
from apps.accounts.models import Account, User
from apps.portfolios.models import Portfolio


@pytest.mark.django_db
def test_experience_is_scoped_sanitized_and_versioned():
    user = cast(User, UserFactory())
    account = cast(Account, AccountFactory())
    other = cast(Account, AccountFactory())
    MembershipFactory(account=account, user=user)
    portfolio = Portfolio.all_objects.create(account=account, title="One", slug="one-career")
    other_portfolio = Portfolio.all_objects.create(account=other, title="Other", slug="other-career")
    client = APIClient()
    client.force_authenticate(user=user)
    url = f"/api/portfolios/{portfolio.id}/experiences/"

    created = client.post(
        url,
        {"title": "Engineer", "organization": "Example", "start_date": "2024-01-01", "description_html": "<p>Trusted<script>x</script></p>"},
        format="json",
    )
    assert created.status_code == 201
    assert created.data["description_html"] == "<p>Trustedx</p>"
    assert client.get(f"/api/portfolios/{other_portfolio.id}/experiences/").status_code == 404

    updated = client.patch(
        f"{url}{created.data['id']}/", {"title": "Senior Engineer"}, format="json", HTTP_IF_MATCH="1"
    )
    assert updated.status_code == 200
    assert updated.data["version"] == 2
