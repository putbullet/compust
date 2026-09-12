from unittest.mock import patch
from fastapi.testclient import TestClient
import httpx

from src.app.services.ai_service import check_ollama_runtime, get_providers_list, set_selected_model


def test_ai_status_when_ollama_connected(client: TestClient) -> None:
    fake_status = {
        "provider": "ollama",
        "url": "http://127.0.0.1:11434",
        "status": "connected",
        "models": [
            {
                "name": "custom-model:latest",
                "size": 1234567,
                "modified_at": "2026-09-11T12:00:00Z",
                "parameter_size": "1B",
                "quantization_level": "Q4_0",
            },
            {
                "name": "llama3:8b",
                "size": 4567890,
                "modified_at": "2026-09-10T12:00:00Z",
                "parameter_size": "8B",
                "quantization_level": "Q8_0",
            },
        ],
        "selected_model": "custom-model:latest",
        "selected_model_available": True,
        "error": None,
    }

    with patch("src.app.main.check_ollama_runtime", return_value=fake_status):
        res = client.get("/api/v1/ai/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "connected"
        assert len(data["models"]) == 2
        model_names = [m["name"] for m in data["models"]]
        assert "custom-model:latest" in model_names
        assert "llama3:8b" in model_names


def test_ai_status_when_ollama_unavailable(client: TestClient) -> None:
    fake_status = {
        "provider": "ollama",
        "url": "http://127.0.0.1:11434",
        "status": "not_running",
        "models": [],
        "selected_model": None,
        "selected_model_available": False,
        "error": "Connection refused",
    }

    with patch("src.app.main.check_ollama_runtime", return_value=fake_status):
        res = client.get("/api/v1/ai/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "not_running"
        assert data["models"] == []


def test_ai_providers_list(client: TestClient) -> None:
    res = client.get("/api/v1/ai/providers")
    assert res.status_code == 200
    providers = res.json()
    assert len(providers) >= 3

    p_ids = {p["id"]: p for p in providers}
    assert "ollama" in p_ids
    assert p_ids["ollama"]["is_local"] is True
    assert p_ids["ollama"]["enabled"] is True

    assert "openai" in p_ids
    assert p_ids["openai"]["enabled"] is False
    assert p_ids["openai"]["status"] == "coming_soon"

    assert "anthropic" in p_ids
    assert p_ids["anthropic"]["enabled"] is False
    assert p_ids["anthropic"]["status"] == "coming_soon"


def test_ai_settings_model_selection(client: TestClient) -> None:
    with patch("src.app.services.ai_service.check_ollama_runtime") as mock_check:
        mock_check.return_value = {
            "provider": "ollama",
            "url": "http://127.0.0.1:11434",
            "status": "connected",
            "models": [{"name": "my-selected-model:latest"}],
            "selected_model": "my-selected-model:latest",
            "selected_model_available": True,
            "error": None,
        }
        res = client.post("/api/v1/ai/settings", json={"selected_model": "my-selected-model:latest"})
        assert res.status_code == 200
        assert res.json()["selected_model"] == "my-selected-model:latest"
