"""
Regression test suite for server resilience, root route handling,
and /health identity document verification.
"""

import pytest
from fastapi.testclient import TestClient
from src.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_identity_document(client):
    """Verify /health returns rich instance identity metadata required by launcher."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "degraded")
    assert data["app"] == "compust"
    assert "version" in data
    assert "mode" in data
    assert "data_dir" in data
    assert "port" in data
    assert "pid" in data


def test_health_deep_endpoint(client):
    """Verify /health/deep checks DB, migrations, frontend build, and Ollama."""
    res = client.get("/health/deep")
    assert res.status_code == 200
    data = res.json()
    assert data["app"] == "compust"
    assert "database" in data
    assert "migrations" in data
    assert "frontend_build" in data
    assert "ollama" in data


def test_root_route_serves_frontend_or_diagnostic(client):
    """Verify GET / never throws NameError or bare 500."""
    res = client.get("/", headers={"accept": "text/html"})
    assert res.status_code == 200
    assert "Compust" in res.text or "<!DOCTYPE html>" in res.text


def test_missing_frontend_renders_friendly_diagnostic(monkeypatch, client):
    """Verify that if frontend dist is missing, GET / serves friendly diagnostics, not 500."""
    import pathlib
    from src.app import main

    fake_missing_path = pathlib.Path("/nonexistent/fake/frontend/dist")
    monkeypatch.setattr(main, "_frontend_dist", fake_missing_path)

    res = client.get("/", headers={"accept": "text/html"})
    assert res.status_code == 200
    assert "Backend Running — Frontend Build Needed" in res.text
    assert "Compust Core Engine" in res.text


def test_global_exception_handler_sanitizes_stack_traces(monkeypatch):
    """Verify unhandled exceptions return a Request ID and never a raw stack trace."""
    from fastapi.testclient import TestClient
    from src.app import paths
    
    def crash():
        raise RuntimeError("Simulated internal backend crash!")

    monkeypatch.setattr(paths, "get_app_mode", crash)

    test_client = TestClient(app, raise_server_exceptions=False)
    res = test_client.get("/health", headers={"accept": "application/json"})
    assert res.status_code == 500
    data = res.json()
    assert data["error"] == "Internal Server Error"
    assert "request_id" in data
    assert data["request_id"].startswith("req_")
    # Verify raw trace is NOT leaked in response
    assert "Simulated internal backend crash!" not in str(data)
