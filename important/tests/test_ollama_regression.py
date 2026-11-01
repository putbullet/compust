import json
import re
from unittest.mock import MagicMock, patch
import httpx
import pytest

from src.app.services.ai_gateway import (
    OllamaProvider,
    generate_completion,
    generate_structured,
    AIUnavailableError,
    AIGatewayError,
    AIProviderType,
)
from src.app.services.job_assistant import _try_extract_json, _format_fallback_reason


def test_ollama_normal_response_and_full_model_name() -> None:
    mock_tags = {
        "models": [
            {"name": "qwen3.5:0.8b", "size": 800000000, "details": {"parameter_size": "0.8B"}},
            {"name": "qwen3.5:4b", "size": 4000000000, "details": {"parameter_size": "4B"}},
        ]
    }
    mock_generate = {"response": "This is a clean AI response.", "done": True}

    def mock_get(url, *args, **kwargs):
        if "/api/tags" in str(url):
            return httpx.Response(200, json=mock_tags, request=httpx.Request("GET", str(url)))
        return httpx.Response(404, request=httpx.Request("GET", str(url)))

    def mock_post(url, *args, **kwargs):
        if "/api/generate" in str(url):
            payload = kwargs.get("json", {})
            # Verify full model name is preserved
            assert payload.get("model") == "qwen3.5:0.8b"
            return httpx.Response(200, json=mock_generate, request=httpx.Request("POST", str(url)))
        return httpx.Response(404, request=httpx.Request("POST", str(url)))

    with patch.object(httpx.Client, "get", side_effect=mock_get):
        with patch.object(httpx.Client, "post", side_effect=mock_post):
            health = OllamaProvider.check_health(force_refresh=True)
            assert health["status"] == "connected"
            assert [m["name"] for m in health["models"]] == ["qwen3.5:0.8b", "qwen3.5:4b"]
            assert health["selected_model"] in ["qwen3.5:0.8b", "qwen3.5:4b"]

            res = OllamaProvider.generate(
                prompt="Hello",
                model="qwen3.5:0.8b",
            )
            assert res == "This is a clean AI response."


def test_ollama_validates_uninstalled_model_and_lists_installed() -> None:
    mock_tags = {
        "models": [
            {"name": "qwen3.5:0.8b", "size": 800000000, "details": {"parameter_size": "0.8B"}},
            {"name": "qwen3.5:4b", "size": 4000000000, "details": {"parameter_size": "4B"}},
        ]
    }

    def mock_get(url, *args, **kwargs):
        return httpx.Response(200, json=mock_tags, request=httpx.Request("GET", str(url)))

    with patch.object(httpx.Client, "get", side_effect=mock_get):
        # 1. Uninstalled model raises AIGatewayError listing installed models
        with pytest.raises(AIGatewayError) as exc_info:
            OllamaProvider.generate(
                prompt="Hello",
                model="uninstalled-model:latest",
            )
        err = str(exc_info.value)
        assert "not installed in Ollama" in err
        assert "qwen3.5:0.8b" in err
        assert "qwen3.5:4b" in err

        # 2. When model is None, it resolves to first installed model
        mock_generate = {"response": "Auto-resolved default", "done": True}
        def mock_post(url, *args, **kwargs):
            payload = kwargs.get("json", {})
            assert payload.get("model") == "qwen3.5:0.8b"
            return httpx.Response(200, json=mock_generate, request=httpx.Request("POST", str(url)))

        with patch.object(httpx.Client, "post", side_effect=mock_post):
            with patch("src.app.services.ai_gateway.get_selected_model", return_value=None):
                res = OllamaProvider.generate(prompt="Hello", model=None)
                assert res == "Auto-resolved default"


def test_ollama_reasoning_style_output_stripped() -> None:
    mock_tags = {"models": [{"name": "qwen3.5:0.8b"}]}
    raw_with_thinking = (
        "<think>\n"
        "Here is internal reasoning.\n"
        "Let us consider how to format JSON.\n"
        "</think>\n"
        '{"status": "success", "score": 95}'
    )
    mock_generate = {"response": raw_with_thinking, "done": True}

    def mock_get(url, *args, **kwargs):
        return httpx.Response(200, json=mock_tags, request=httpx.Request("GET", str(url)))

    def mock_post(url, *args, **kwargs):
        return httpx.Response(200, json=mock_generate, request=httpx.Request("POST", str(url)))

    with patch.object(httpx.Client, "get", side_effect=mock_get):
        with patch.object(httpx.Client, "post", side_effect=mock_post):
            parsed = generate_structured(
                prompt="Evaluate candidate",
                model="qwen3.5:0.8b",
                provider=AIProviderType.OLLAMA,
            )
            assert isinstance(parsed, dict)
            assert parsed.get("status") == "success"
            assert parsed.get("score") == 95

    # Also verify _try_extract_json helper directly
    extracted = _try_extract_json(raw_with_thinking)
    assert extracted == {"status": "success", "score": 95}


def test_ollama_model_not_found_404_error() -> None:
    mock_tags = {"models": []}  # No models installed

    def mock_get(url, *args, **kwargs):
        return httpx.Response(200, json=mock_tags, request=httpx.Request("GET", str(url)))

    def mock_post(url, *args, **kwargs):
        return httpx.Response(404, text='{"error":"model \'llama3\' not found"}', request=httpx.Request("POST", str(url)))

    with patch.object(httpx.Client, "get", side_effect=mock_get):
        with patch.object(httpx.Client, "post", side_effect=mock_post):
            with pytest.raises((AIGatewayError, AIUnavailableError)) as exc:
                OllamaProvider.generate(prompt="Hi", model="llama3")
            assert "not" in str(exc.value).lower()


def test_ollama_slow_response_timeout() -> None:
    mock_tags = {"models": [{"name": "qwen3.5:0.8b"}]}

    def mock_get(url, *args, **kwargs):
        return httpx.Response(200, json=mock_tags, request=httpx.Request("GET", str(url)))

    def mock_post(url, *args, **kwargs):
        raise httpx.TimeoutException("Read timed out after 2.0s")

    with patch.object(httpx.Client, "get", side_effect=mock_get):
        with patch.object(httpx.Client, "post", side_effect=mock_post):
            with pytest.raises(AIGatewayError) as exc:
                OllamaProvider.generate(prompt="Hi", model="qwen3.5:0.8b", timeout_seconds=2.0)
            assert "timed out" in str(exc.value).lower()


def test_ollama_server_down_connection_refused() -> None:
    def mock_get(url, *args, **kwargs):
        raise httpx.ConnectError("Connection refused on 127.0.0.1:11434")

    with patch.object(httpx.Client, "get", side_effect=mock_get):
        with patch.object(httpx.Client, "post", side_effect=mock_get):
            health = OllamaProvider.check_health(force_refresh=True)
            assert health["status"] == "not_running"
            assert "could not connect" in health["error"].lower()

            with pytest.raises(AIUnavailableError) as exc:
                OllamaProvider.generate(prompt="Hi")
            assert "unreachable" in str(exc.value).lower() or "cannot reach" in str(exc.value).lower()


def test_fallback_reason_diagnostics() -> None:
    e_conn = httpx.ConnectError("Connection refused")
    reason_conn = _format_fallback_reason(e_conn, "Ollama", "qwen3.5:0.8b")
    assert "unreachable" in reason_conn.lower()

    e_404 = AIGatewayError("Model 'llama3' not found in Ollama")
    reason_404 = _format_fallback_reason(e_404, "Ollama", "llama3")
    assert "not found" in reason_404.lower()

    e_timeout = httpx.TimeoutException("Timed out")
    reason_to = _format_fallback_reason(e_timeout, "Ollama", "qwen3.5:0.8b")
    assert "timed out" in reason_to.lower()

    e_json = json.JSONDecodeError("Expecting value", "raw", 0)
    reason_json = _format_fallback_reason(e_json, "Ollama", "qwen3.5:0.8b")
    assert "invalid json" in reason_json.lower()


def test_provider_switching_model_isolation(db_session=None) -> None:
    from src.app.services.ai_gateway import (
        save_user_ai_settings,
        get_ai_status,
        get_selected_model,
        AIProviderType,
    )
    from src.app.database import SessionLocal

    with SessionLocal() as db:
        # Step 1: Configure Ollama with qwen3.5:4b
        save_user_ai_settings(db, user_id=1, updates={
            "active_provider": "ollama",
            "selected_model": "qwen3.5:4b",
            "ollama_model": "qwen3.5:4b",
        })
        status1 = get_ai_status(db, user_id=1)
        assert status1["active_provider"] == "ollama"
        assert status1["selected_models"]["ollama"] == "qwen3.5:4b"

        # Step 2: Switch to Gemini with gemini-3.5-flash
        save_user_ai_settings(db, user_id=1, updates={
            "active_provider": "gemini",
            "selected_model": "gemini-3.5-flash",
            "gemini_model": "gemini-3.5-flash",
        })
        status2 = get_ai_status(db, user_id=1)
        assert status2["active_provider"] == "gemini"
        assert status2["selected_models"]["gemini"] == "gemini-3.5-flash"
        # Ollama model must NOT have been overwritten by gemini-3.5-flash
        assert status2["selected_models"]["ollama"] == "qwen3.5:4b"

        # Step 3: Switch back to Ollama
        save_user_ai_settings(db, user_id=1, updates={
            "active_provider": "ollama",
            "selected_model": "qwen3.5:4b",
        })
        status3 = get_ai_status(db, user_id=1)
        assert status3["active_provider"] == "ollama"
        assert status3["selected_models"]["ollama"] == "qwen3.5:4b"
        assert status3["selected_models"]["gemini"] == "gemini-3.5-flash"


def test_ollama_status_no_infinite_recursion_when_cloud_model_in_db() -> None:
    """Verify get_ai_status never triggers infinite recursion when selected_model is a cloud model."""
    from src.app.services.ai_gateway import get_ai_status, save_user_ai_settings
    from src.app.database import SessionLocal

    with SessionLocal() as db:
        # Simulate legacy/cloud selected_model stored in user settings
        save_user_ai_settings(db, user_id=1, updates={
            "active_provider": "gemini",
            "selected_model": "gemini-3.5-flash-lite",
            "gemini_model": "gemini-3.5-flash-lite",
        })

        # This previously triggered RecursionError between check_health and get_selected_model
        status = get_ai_status(db, user_id=1)
        assert status is not None
        assert status["ollama"] is not None
        assert status["ollama"]["provider"] == "ollama"
        assert not (status["selected_models"]["ollama"] or "").startswith("gemini-")
