"""
Tests for both health endpoints. These are the only endpoints that
exist in Phase 2, so this is also, right now, the smoke test that the
app starts up and routes correctly.
"""


def test_root_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_versioned_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body


def test_unknown_route_returns_clean_404(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    # Confirms the centralized handler shape is used, not FastAPI's raw default
    assert "error" in body
    assert body["error"]["code"] == "http_error"
