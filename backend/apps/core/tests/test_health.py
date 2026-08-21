from typing import cast

from django.test import Client

from apps.core import health


def test_healthz():
    response = Client().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz():
    response = Client().get("/readyz")
    assert response.status_code in {200, 503}
    assert set(response.json()["checks"]) == {"db", "redis", "storage", "broker"}


def test_readyz_uses_configured_s3_client(monkeypatch):
    calls: dict[str, object] = {}

    class StorageClient:
        def list_buckets(self):
            calls["listed"] = True

    def client(service_name, **kwargs):
        calls["service_name"] = service_name
        calls["kwargs"] = kwargs
        return StorageClient()

    monkeypatch.setattr(health.boto3, "client", client)
    response = Client().get("/readyz")
    assert calls["service_name"] == "s3"
    kwargs = cast(dict[str, object], calls["kwargs"])
    assert kwargs["endpoint_url"] == "http://localhost:9000"
    assert calls["listed"] is True
    assert response.json()["checks"]["storage"] == "ok"
