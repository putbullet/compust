import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.services.ai_gateway import (
    GeminiProvider,
    OpenAIProvider,
    _MODELS_CATALOG_CACHE,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_gemini_fallback_clean_seeds():
    """Fallback models must not contain retired 1.0, 1.5, or 2.5-flash models."""
    seeds = GeminiProvider.FALLBACK_MODELS
    assert len(seeds) >= 3
    for m in seeds:
        model_id = m["id"].lower()
        assert not any(bad in model_id for bad in ["1.0", "1.5", "2.5-flash", "text-bison"]), f"Retired model in seeds: {model_id}"
    assert any("3.5-flash" in m["id"] for m in seeds)


def test_openai_fallback_clean_seeds():
    """Fallback models must not contain retired gpt-3.5 or fictional o4-mini."""
    seeds = OpenAIProvider.FALLBACK_MODELS
    assert len(seeds) >= 3
    for m in seeds:
        model_id = m["id"].lower()
        assert not any(bad in model_id for bad in ["gpt-3.5", "o4-mini", "realtime"]), f"Invalid model in seeds: {model_id}"
    assert any("gpt-4o-mini" in m["id"] for m in seeds)


def test_gemini_filtering_excludes_retired_and_specialized():
    """Dynamic discovery must strictly filter out retired models and specialized non-chat models."""
    fake_api_response = {
        "models": [
            {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini 1.5 Flash"},
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini 2.5 Flash"},
            {"name": "models/gemini-2.5-flash-tts", "supportedGenerationMethods": ["generateContent"], "displayName": "TTS Model"},
            {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini 3.5 Flash"},
            {"name": "models/gemini-3.1-flash-lite", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini 3.1 Flash Lite"},
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"], "displayName": "Embedding"},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_api_response

    _MODELS_CATALOG_CACHE.clear()

    with patch("httpx.Client.get", return_value=mock_resp):
        catalog = GeminiProvider.get_models_catalog(api_key="fake-test-key", probe=False, force_refresh=True)
        model_ids = [m["id"] for m in catalog["models"]]

        # Clean models present
        assert "gemini-3.5-flash" in model_ids
        assert "gemini-3.1-flash-lite" in model_ids

        # Retired models excluded
        assert "gemini-1.5-flash" not in model_ids
        assert "gemini-2.5-flash" not in model_ids

        # Specialized / non-chat models excluded
        assert "gemini-2.5-flash-tts" not in model_ids
        assert "text-embedding-004" not in model_ids


def test_gemini_sequential_probing_categories():
    """Sequential probing must classify models into Available and May require paid plan without bursting."""
    fake_api_response = {
        "models": [
            {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini 3.5 Flash"},
            {"name": "models/gemini-pro-latest", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini Pro Latest"},
        ]
    }

    def mock_post(url, *args, **kwargs):
        resp = MagicMock()
        if "gemini-3.5-flash" in url:
            resp.status_code = 200
            resp.json.return_value = {}
        elif "gemini-pro-latest" in url:
            resp.status_code = 429
            resp.json.return_value = {"error": "Quota exceeded"}
        else:
            resp.status_code = 500
        return resp

    mock_get = MagicMock()
    mock_get.status_code = 200
    mock_get.json.return_value = fake_api_response

    _MODELS_CATALOG_CACHE.clear()

    with patch("httpx.Client.get", return_value=mock_get), \
         patch("httpx.Client.post", side_effect=mock_post):
        catalog = GeminiProvider.get_models_catalog(api_key="fake-key", probe=True, force_refresh=True)
        categories = catalog["categories"]

        avail_ids = [m["id"] for m in categories["available"]]
        paid_ids = [m["id"] for m in categories["requires_paid"]]

        assert "gemini-3.5-flash" in avail_ids
        assert "gemini-pro-latest" in paid_ids


def test_models_cache_and_force_refresh():
    """Cached results must be returned until force_refresh is requested."""
    _MODELS_CATALOG_CACHE.clear()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [
        {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"]}
    ]}

    with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        # First call hits mock
        res1 = GeminiProvider.get_models_catalog(api_key="cache-key", probe=False, force_refresh=False)
        assert res1["cached"] is False
        assert mock_get.call_count == 1

        # Second call returns from cache
        res2 = GeminiProvider.get_models_catalog(api_key="cache-key", probe=False, force_refresh=False)
        assert res2["cached"] is True
        assert mock_get.call_count == 1

        # Force refresh bypasses cache
        res3 = GeminiProvider.get_models_catalog(api_key="cache-key", probe=False, force_refresh=True)
        assert res3["cached"] is False
        assert mock_get.call_count == 2


def test_api_models_endpoint(client):
    """FastAPI endpoint /api/v1/ai/models/{provider} returns categorized model catalog."""
    resp = client.get("/api/v1/ai/models/gemini")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gemini"
    assert "categories" in data
    assert "available" in data["categories"]
    assert "requires_paid" in data["categories"]
    assert "unverified" in data["categories"]
    assert len(data["models"]) > 0


def test_api_models_probe_endpoint(client):
    """FastAPI POST endpoint /api/v1/ai/models/{provider}/probe triggers probe."""
    resp = client.post("/api/v1/ai/models/gemini/probe")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gemini"
    assert "categories" in data
