"""
Unit and Integration Tests for Alex AI Interviewer Video System.

Tests:
1. Question text hash computation and normalization
2. Video registry asset lookup and hash mismatch protection
3. Missing asset safe fallback (returns None, never raises or breaks)
4. Integration with MockInterviewService slot-to-question conversion
5. FastAPI endpoints: /interviewer/ media serving and /api/v1/mock-interview/interviewer-status
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.services.alex_video_service import (
    AlexVideoService,
    compute_question_hash,
    normalize_text_for_hash,
    alex_video_service,
)
from src.app.services.mock_interview_engine import QuestionSlot
from src.app.services.mock_interview_service import MockInterviewService


@pytest.fixture
def client():
    return TestClient(app)


def test_question_text_hash_normalization():
    """Verify text normalization is insensitive to casing, extra spaces, and markdown."""
    base_text = "What is the CIA Triad?"
    variants = [
        "what is the cia triad?",
        "  WHAT IS THE CIA TRIAD?  ",
        "What is the **CIA** Triad?",
        "What is the `CIA` Triad?",
        "What   is   the   CIA   Triad?  \n",
    ]
    base_hash = compute_question_hash(base_text)
    assert len(base_hash) == 16

    for variant in variants:
        variant_hash = compute_question_hash(variant)
        assert variant_hash == base_hash, f"Hash mismatch for variant '{variant}'"


def test_hash_mismatch_prevents_stale_video_reuse(tmp_path):
    """If question text was altered, get_video_for_question must return None."""
    dummy_registry_file = tmp_path / "test_registry.json"
    service = AlexVideoService(registry_file=dummy_registry_file)

    original_text = "What is the difference between authentication and authorization?"
    altered_text = "Can you explain the differences between authentication and authorization in cloud systems?"

    # Register original
    service.register_video(
        question_id="sec_auth_vs_authz",
        question_text=original_text,
        video_path="/interviewer/alex/security_engineering/technical/sec_auth_vs_authz.mp4",
        question_type="technical",
        track="security_engineering",
    )

    # When queried with altered text, must fail hash check and return None
    result = service.get_video_for_question("sec_auth_vs_authz", altered_text)
    assert result is None, "Should not return video when question text has changed!"


def test_missing_asset_returns_none_gracefully(tmp_path):
    """When video file is not on disk, return None instead of failing."""
    dummy_registry_file = tmp_path / "test_registry.json"
    service = AlexVideoService(registry_file=dummy_registry_file)

    question_text = "What is a non-existent question?"
    service.register_video(
        question_id="non_existent_q",
        question_text=question_text,
        video_path="/interviewer/alex/security_engineering/technical/non_existent_file_12345.mp4",
        question_type="technical",
    )

    # The file does not exist on disk, so get_video_for_question must return None
    result = service.get_video_for_question("non_existent_q", question_text)
    assert result is None


def test_interviewer_status_endpoint(client):
    """Test /api/v1/mock-interview/interviewer-status returns valid metadata."""
    response = client.get("/api/v1/mock-interview/interviewer-status")
    assert response.status_code == 200
    data = response.json()
    assert data["interviewer"] == "alex"
    assert "total_registered" in data
    assert "available_on_disk" in data
    assert "reference_portrait" in data


def test_interviewer_media_serving(client):
    """Test /interviewer/ serves static portrait file."""
    response = client.get("/interviewer/alex/identity/reference.jpg")
    assert response.status_code == 200
    assert "image" in response.headers.get("content-type", "")
    assert len(response.content) > 1000


def test_slot_to_next_question_includes_interviewer_metadata():
    """Test MockInterviewService._slot_to_next_question populates interviewer fields."""
    interview_svc = MockInterviewService()
    slot = QuestionSlot(
        question_id="sec_f_14",
        competency="technical",
        competency_label="Technical",
        title="What is the CIA Triad?",
        expected_duration_seconds=90,
    )
    next_q = interview_svc._slot_to_next_question(slot)
    assert "Alex" in next_q.interviewer_name
    # Should have interviewer_video_url field present in model schema
    assert hasattr(next_q, "interviewer_video_url")
    assert hasattr(next_q, "interviewer_audio_url")
