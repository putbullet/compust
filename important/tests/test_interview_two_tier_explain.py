import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)
SLUG = "ai-what-is-the-transformer-architecture-and-how-does-self-attention-work"
TRACK = "ai_tech_interview"

def test_instant_pre_explanation_endpoint():
    """Verify GET explanation returns deterministic pre-explanation fast without AI inference."""
    response = client.get(f"/api/v1/interview-prep/questions/{TRACK}/{SLUG}/explanation")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["slug"] == SLUG
    assert data["track"] == TRACK
    assert "tldr" in data and data["tldr"]
    assert "simple_explanation" in data and data["simple_explanation"]
    assert isinstance(data["key_terms"], list)
    # Default flags check
    assert isinstance(data["needs_code"], bool)
    assert isinstance(data["needs_diagram"], bool)
    # No AI jargon in explanation
    assert "curated question context baseline" not in (data["simple_explanation"] or "").lower()
    assert "active ai provider offline" not in (data["simple_explanation"] or "").lower()

def test_deep_dive_offline_graceful_handling():
    """When AI provider fails, endpoint returns clear neutral failure without baseline jargon."""
    with patch("src.app.services.ai_gateway.generate_completion", side_effect=RuntimeError("Connection refused by Ollama host")):
        response = client.post(
            f"/api/v1/interview-prep/questions/{TRACK}/{SLUG}/deep-dive",
            json={"language": "en", "force_regenerate": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["can_retry"] is True
        assert data["error_reason"] is not None
        # Must be neutral error, zero fallback jargon
        assert "curated question context baseline" not in data["error_reason"].lower()
        assert "baseline" not in data["error_reason"].lower()

def test_deep_dive_successful_synthesis():
    """When AI succeeds, structured deep dive is returned and cached."""
    mock_ai_json = (
        '{"deeper_explanation": "Self-attention computes scaled dot products across query and key matrices.", '
        '"extra_example": "O(N^2) memory footprint during long sequences leading to GPU OOM.", '
        '"pitfalls": ["Over-allocation of KV cache", "Quadratic scaling bottlenecks"], '
        '"interview_followups": ["How does FlashAttention optimize the memory IO bound?", "Why scale by sqrt(d_k)?"], '
        '"has_code": false, "code_language": null, "code_snippet": null, "has_diagram": false, "diagram_svg": null}'
    )
    with patch("src.app.services.ai_gateway.generate_completion", return_value=mock_ai_json):
        response = client.post(
            f"/api/v1/interview-prep/questions/{TRACK}/{SLUG}/deep-dive",
            json={"language": "en", "force_regenerate": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deep_dive"] is not None
        dd = data["deep_dive"]
        assert "Self-attention" in dd["deeper_explanation"]
        assert len(dd["interview_followups"]) == 2
        assert dd["extra_example"]

        # Verify it is now cached in subsequent GET explanation call
        get_res = client.get(f"/api/v1/interview-prep/questions/{TRACK}/{SLUG}/explanation")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["cached_deep_dive"] is not None
        assert get_data["cached_deep_dive"]["deeper_explanation"] == dd["deeper_explanation"]
