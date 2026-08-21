from django.test import Client


def test_healthz():
    response = Client().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz():
    response = Client().get("/readyz")
    assert response.status_code in {200, 503}
    assert set(response.json()["checks"]) == {"db", "redis", "storage", "broker"}
