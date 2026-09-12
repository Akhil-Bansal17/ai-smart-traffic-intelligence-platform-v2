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


def test_versioned_readiness_endpoint(client):
    """Verifies that /api/v1/health/readiness returns structured dependency diagnostics."""
    response = client.get("/api/v1/health/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ready", "degraded")
    assert "dependencies" in body
    assert "database" in body["dependencies"]
    assert "storage" in body["dependencies"]
    assert "configuration" in body["dependencies"]
    assert body["dependencies"]["database"]["status"] == "healthy"
    assert body["dependencies"]["database"]["latency_ms"] is not None


def test_root_readiness_endpoint(client):
    """Verifies that unversioned /readiness functions as an infra-level readiness probe."""
    response = client.get("/readiness")
    assert response.status_code == 200
    body = response.json()
    assert "dependencies" in body
    assert body["is_ready"] is True

