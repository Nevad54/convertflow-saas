from __future__ import annotations

from fastapi.testclient import TestClient


def test_local_app_hides_saas_routes():
    import app_local

    client = TestClient(app_local.app, raise_server_exceptions=True)

    home = client.get("/")
    assert home.status_code == 200
    assert "Open the local workspace" in home.text
    assert "See Free vs Pro" not in home.text

    pricing = client.get("/pricing")
    assert pricing.status_code == 404

    dashboard = client.get("/dashboard", follow_redirects=False)
    assert dashboard.status_code == 303
    assert dashboard.headers["location"] == "/"


def test_saas_app_exposes_pricing():
    import app_saas

    client = TestClient(app_saas.app, raise_server_exceptions=True)

    home = client.get("/")
    assert home.status_code == 200
    assert "See Free vs Pro" in home.text

    pricing = client.get("/pricing")
    assert pricing.status_code == 200
