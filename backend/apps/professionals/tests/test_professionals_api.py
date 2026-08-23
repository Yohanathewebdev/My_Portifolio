from typing import cast

import pytest
from rest_framework.test import APIClient

from apps.accounts.factories import AccountFactory, MembershipFactory, UserFactory
from apps.accounts.models import Account, User
from apps.portfolios.models import Portfolio
from apps.professionals.models import Profession


@pytest.mark.django_db
def test_active_professions_are_listed_and_assignments_are_portfolio_scoped():
    user = cast(User, UserFactory())
    account = cast(Account, AccountFactory())
    MembershipFactory(account=account, user=user)
    portfolio = Portfolio.all_objects.create(account=account, title="One", slug="one-profession")
    active = Profession.objects.create(name="Developer", slug="developer")
    Profession.objects.create(name="Retired", slug="retired", is_active=False)
    client = APIClient()
    client.force_authenticate(user=user)

    listed = client.get("/api/professions/")
    assert listed.status_code == 200
    assert [item["slug"] for item in listed.data["results"]] == ["developer"]

    url = f"/api/portfolios/{portfolio.id}/professions/"
    assigned = client.post(url, {"profession": str(active.id), "is_primary": True}, format="json")
    assert assigned.status_code == 201
    assert str(client.get(url).data["results"][0]["profession"]) == str(active.id)
