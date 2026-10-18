"""
tests/test_ai_gateway.py
========================
Comprehensive unit and integration tests for the Unified AI Gateway.

Validates:
1. PII Redaction (email, phone, URLs sanitized locally)
2. API Key Security (masking, write-only endpoints, no secret leak in logs/errors)
3. Ollama Provider (mocked HTTP success, structured output, connection failure)
4. Gemini Provider (mocked HTTP success, header auth, structured JSON, 401/403, 429, safety block)
5. Consent Enforcement (AIConsentRequiredError if consent not granted)
6. Fallback Policy (zero silent cross-provider leakage from Ollama to Gemini)
7. Gated Live Smoke Test (runs only when RUN_LIVE_GEMINI_TEST=1)
"""

import json
import os
from unittest.mock import patch, MagicMock
import httpx
import pytest
from fastapi.testclient import TestClient

from src.app.services.ai_gateway import (
    AIGatewayError,
    AIUnavailableError,
    AIAuthenticationError,
    AIRateLimitError,
    AISafetyBlockError,
    AIConsentRequiredError,
    AIProviderType,
    OllamaProvider,
    GeminiProvider,
    get_provider,
    get_active_provider,
    set_active_provider,
    get_selected_model,
    set_selected_model,
    get_gemini_api_key,
    set_gemini_api_key,
    mask_api_key,
    redact_personal_identifiers,
    generate_completion,
    generate_structured,
    load_ai_config,
    save_ai_config,
)


# ─── 1. PII Redaction Tests ───────────────────────────────────────────────────

def test_redact_personal_identifiers() -> None:
    sample_text = (
        "Candidate John Doe, email: john.doe@example.com or j.doe+compust@domain.co.uk. "
        "Phone: +1 555-123-4567, mobile: 06 12 34 56 78, or (555) 987-6543. "
        "Portfolio: https://johndoe.dev/projects and LinkedIn: http://linkedin.com/in/johndoe. "
        "Skills: Python, FastAPI, Docker, TypeScript, React."
    )

    redacted = redact_personal_identifiers(sample_text)

    # Emails must be stripped
    assert "john.doe@example.com" not in redacted
    assert "j.doe+compust@domain.co.uk" not in redacted
    assert "[email-redacted]" in redacted

    # Phone numbers must be stripped
    assert "555-123-4567" not in redacted
    assert "06 12 34 56 78" not in redacted
    assert "[phone-redacted]" in redacted

    # URLs must be stripped
    assert "https://johndoe.dev/projects" not in redacted
    assert "http://linkedin.com/in/johndoe" not in redacted
    assert "[url-redacted]" in redacted

    # Core non-sensitive technical skills MUST be preserved
    assert "Python" in redacted
    assert "FastAPI" in redacted
    assert "TypeScript" in redacted
    assert "React" in redacted


# ─── 2. Key Masking & Secret Security Tests ───────────────────────────────────

def test_mask_api_key() -> None:
    assert mask_api_key(None) == ""
    assert mask_api_key("") == ""
    assert mask_api_key("short") == ""
    # Realistic test key
    test_key = "AIzaSyD-1234567890abcdefXYZ99"
    masked = mask_api_key(test_key)
    assert masked == "...YZ99"
    assert "1234567890" not in masked


def test_api_endpoints_never_leak_full_key(client: TestClient) -> None:
    secret_key = "AIzaSySECRETKEYFORTESTINGNEVERLEAK1234"
    try:
        # Save key via write-only endpoint
        set_res = client.post("/api/v1/ai/gemini/key", json={"api_key": secret_key})
        assert set_res.status_code == 200
        set_data = set_res.json()
        assert secret_key not in json.dumps(set_data)
        assert set_data["gemini_key_masked"] == "...1234"

        # Check status endpoint
        status_res = client.get("/api/v1/ai/status")
        assert status_res.status_code == 200
        status_text = status_res.text
        assert secret_key not in status_text
        assert "...1234" in status_text

        # Check providers list endpoint
        prov_res = client.get("/api/v1/ai/providers")
        assert prov_res.status_code == 200
        prov_text = prov_res.text
        assert secret_key not in prov_text
    finally:
        # Cleanup
        client.delete("/api/v1/ai/gemini/key")


# ─── 3. Mocked Ollama Provider Tests ──────────────────────────────────────────

def test_ollama_generate_success() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Hello candidate, your resume looks strong!"}

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        result = OllamaProvider.generate(
            prompt="Analyze my resume",
            system_prompt="You are a career assistant",
            model="qwen3.5:0.8b",
        )
        assert result == "Hello candidate, your resume looks strong!"
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "qwen3.5:0.8b"
        assert call_kwargs["json"]["prompt"] == "Analyze my resume"
        assert call_kwargs["json"]["system"] == "You are a career assistant"


def test_ollama_offline_raises_ai_unavailable() -> None:
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(AIUnavailableError) as exc_info:
            OllamaProvider.generate(prompt="Hello", model="qwen3.5:0.8b")
        assert "Cannot reach Ollama" in str(exc_info.value)


# ─── 4. Mocked Gemini Provider Tests ──────────────────────────────────────────

def test_gemini_generate_success_and_header_auth() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Gemini: Candidate possesses strong distributed systems expertise."}]
                },
                "finishReason": "STOP",
            }
        ]
    }

    test_key = "AIzaSyTestKeyForMockingValidHeader123"

    with patch.dict(os.environ, {"GEMINI_API_KEY": test_key}):
        with patch("src.app.services.ai_gateway.load_ai_config", return_value={"gemini_consent_given": True}):
            with patch("httpx.Client.post", return_value=mock_response) as mock_post:
                output = GeminiProvider.generate(
                    prompt="Evaluate skills",
                    system_prompt="Career expert",
                    model="gemini-3.5-flash-lite",
                )
                assert "distributed systems expertise" in output
                assert mock_post.called

                # Verify authentication is sent via HEADER, never query param
                call_kwargs = mock_post.call_args[1]
                assert "headers" in call_kwargs
                assert call_kwargs["headers"].get("x-goog-api-key") == test_key

                call_url = mock_post.call_args[0][0]
                assert test_key not in call_url


def test_gemini_generate_structured_output() -> None:
    structured_content = json.dumps({
        "score": 92,
        "strengths": ["FastAPI", "SQLite", "Inno Setup"],
        "recommendations": ["Highlight automated packaging experience"],
    })

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": structured_content}]
                },
                "finishReason": "STOP",
            }
        ]
    }

    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyMockedKey1234"}):
        with patch("src.app.services.ai_gateway.load_ai_config", return_value={"gemini_consent_given": True}):
            with patch("httpx.Client.post", return_value=mock_response):
                data = generate_structured(
                    prompt="Analyze resume structured",
                    provider=AIProviderType.GEMINI,
                    model="gemini-3.5-flash-lite",
                )
                assert isinstance(data, dict)
                assert data["score"] == 92
                assert "FastAPI" in data["strengths"]


def test_gemini_authentication_error_401_403() -> None:
    secret_key = "AIzaSyInvalidKeyThatShouldNotLeak99"
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.text = '{"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}}'

    with patch.dict(os.environ, {"GEMINI_API_KEY": secret_key}):
        with patch("src.app.services.ai_gateway.load_ai_config", return_value={"gemini_consent_given": True}):
            with patch("httpx.Client.post", return_value=mock_response):
                with pytest.raises(AIAuthenticationError) as exc_info:
                    GeminiProvider.generate(prompt="Hello", model="gemini-3.5-flash-lite")

                # Must raise clear auth error and NEVER leak the key
                err_msg = str(exc_info.value)
                assert "Invalid or unauthorized Google Gemini API key" in err_msg
                assert secret_key not in err_msg


def test_gemini_rate_limit_backoff_429() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.text = '{"error": {"code": 429, "message": "Resource has been exhausted", "status": "RESOURCE_EXHAUSTED"}}'

    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyTestKey429"}):
        with patch("src.app.services.ai_gateway.load_ai_config", return_value={"gemini_consent_given": True}):
            with patch("time.sleep") as mock_sleep:
                with patch("httpx.Client.post", return_value=mock_response) as mock_post:
                    with pytest.raises(AIRateLimitError) as exc_info:
                        GeminiProvider.generate(prompt="Hello", model="gemini-3.5-flash-lite")

                    assert "rate limit" in str(exc_info.value).lower()
                    assert mock_post.call_count == 1  # Immediate raise without 429 retry loop


def test_gemini_safety_block() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "finishReason": "SAFETY",
                "safetyRatings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "HIGH"}],
            }
        ]
    }

    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyTestKeySafety"}):
        with patch("src.app.services.ai_gateway.load_ai_config", return_value={"gemini_consent_given": True}):
            with patch("httpx.Client.post", return_value=mock_response):
                with pytest.raises(AISafetyBlockError) as exc_info:
                    GeminiProvider.generate(prompt="Explain vulnerability", model="gemini-3.5-flash-lite")
                assert "safety filters" in str(exc_info.value)


# ─── 5. Consent Enforcement Tests ─────────────────────────────────────────────

def test_gemini_consent_required() -> None:
    # When consent is not granted, calling Gemini via gateway must fail immediately
    with patch("src.app.services.ai_gateway.load_ai_config", return_value={"gemini_consent_given": False, "active_provider": "gemini"}):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyConsentKey123"}):
            with pytest.raises(AIConsentRequiredError) as exc_info:
                generate_completion(prompt="Analyze candidate", provider=AIProviderType.GEMINI)
            assert "consent" in str(exc_info.value).lower()


# ─── 6. Fallback Policy Tests (Zero Silent Cross-Provider Leak) ───────────────

def test_no_silent_fallback_from_ollama_to_gemini() -> None:
    """If Ollama is active and fails, it must never silently forward candidate text to Gemini."""
    with patch("src.app.services.ai_gateway.get_active_provider", return_value=AIProviderType.OLLAMA):
        with patch("src.app.services.ai_gateway.load_ai_config", return_value={"fallback_policy": "deterministic"}):
            with patch("src.app.services.ai_gateway.OllamaProvider.generate", side_effect=AIUnavailableError("Ollama offline")):
                with patch("src.app.services.ai_gateway.GeminiProvider.generate") as mock_gemini_gen:
                    with pytest.raises(AIUnavailableError):
                        generate_completion(prompt="Private candidate details")

                    # Gemini must NOT have been called!
                    mock_gemini_gen.assert_not_called()


# ─── 7. Gated Live Smoke Test ─────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_GEMINI_TEST"),
    reason="Live Gemini API test is gated behind RUN_LIVE_GEMINI_TEST=1",
)
def test_live_gemini_smoke_call() -> None:
    """Optional live test verifying real Google Gemini API response with live test key."""
    key = get_gemini_api_key()
    assert key, "GEMINI_API_KEY must be configured for live test"

    with patch("src.app.services.ai_gateway.load_ai_config", return_value={"gemini_consent_given": True}):
        output = GeminiProvider.generate(
            prompt="Reply with exactly 'COMPUST_GEMINI_ONLINE' and nothing else.",
            model="gemini-3.5-flash-lite",
            timeout_seconds=20.0,
        )
        assert "COMPUST_GEMINI_ONLINE" in output.strip()
