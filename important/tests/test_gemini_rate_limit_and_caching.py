"""
tests/test_gemini_rate_limit_and_caching.py
============================================
Unit & regression tests for Gemini rate limit handling, caching,
and on-demand application materials generation.
"""
from __future__ import annotations

import time
import threading
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.models import Base, User, Resume
from src.app.schemas_job_assistant import (
    ExternalJobInput,
    SupportedLanguage,
    MaterialType,
    RegenerateMaterialRequest,
)
from src.app.services.ai_gateway import AIRateLimitError, AIProviderType
from src.app.services.job_assistant import (
    run_job_target_analysis,
    regenerate_single_material,
    _ANALYSIS_CACHE,
    _MATERIAL_CACHE,
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = User(
        id=1, email="candidate@compust.internal", password_hash="hash",
        first_name="Ana", last_name="Silva", is_active=True,
        created_at=now, updated_at=now,
    )
    db.add(user)
    db.commit()

    resume = Resume(
        id=1,
        user_id=1,
        title="Ana Silva - Senior Engineer",
        created_at=now,
        updated_at=now,
        structured_data={
            "profile": {"full_name": "Ana Silva", "headline": "Senior Software Engineer", "summary": "FastAPI and Python lead"},
            "skills": [{"id": "s1", "name": "Python"}, {"id": "s2", "name": "FastAPI"}, {"id": "s3", "name": "Docker"}],
            "experience": [{"id": "e1", "title": "Staff Backend Engineer", "company": "CloudCorp", "description": "Designed APIs."}],
            "education": [{"id": "ed1", "degree": "B.Sc.", "field": "Computer Science", "institution": "University"}],
            "projects": [],
            "certifications": [],
            "languages": [{"id": "l1", "language": "English"}],
        },
    )
    db.add(resume)
    db.commit()

    yield db, user, resume
    db.close()


def test_on_demand_materials_not_pregenerated(test_db):
    """
    Initial job analysis MUST NOT pre-generate cold email, DM, or motivation letter.
    Stage 4 materials must be returned as ungenerated (generated=False, error='')
    so they do not burn AI quota speculatively.
    """
    db, user, resume = test_db
    job_input = ExternalJobInput(
        target_role="Senior Python Engineer",
        job_description="We need an expert in Python and Docker to build distributed systems.",
        language=SupportedLanguage.EN,
    )

    with patch("src.app.services.job_assistant._cloud_single_pass_analysis") as mock_cloud:
        from src.app.schemas_job_assistant import JobRequirement, MatchAnalysis, ResumeRecommendation, RequirementCategory, RequirementImportance, MatchStatus, RecommendationType
        mock_cloud.return_value = (
            [JobRequirement(text="Python", category=RequirementCategory.TECHNICAL_SKILL, importance=RequirementImportance.REQUIRED, raw_keyword="python")],
            MatchAnalysis(),
            [ResumeRecommendation(id="r1", rec_type=RecommendationType.EMPHASIZE, section="skills", reason="Highlight Python", suggested_text="Python", current_text="Python")],
        )

        with patch("src.app.services.job_assistant.get_active_provider", return_value=AIProviderType.GEMINI), \
             patch("src.app.services.job_assistant.is_ai_available", return_value=True):
            result = run_job_target_analysis(db, user.id, resume, job_input)

    assert result.cold_email.generated is False
    assert result.cold_email.error == ""
    assert result.short_message.generated is False
    assert result.short_message.error == ""
    assert result.motivation_letter.generated is False
    assert result.motivation_letter.error == ""


def test_analysis_caching_prevents_duplicate_api_calls(test_db):
    """
    Re-analyzing the same job + resume version must reuse the cached analysis
    and make 0 subsequent LLM calls.
    """
    db, user, resume = test_db
    job_input = ExternalJobInput(
        target_role="Platform Engineer",
        job_description="Kubernetes, Terraform, AWS experience required." * 3,
        language=SupportedLanguage.EN,
    )

    with patch("src.app.services.job_assistant._cloud_single_pass_analysis") as mock_cloud, \
         patch("src.app.services.job_assistant.get_active_provider", return_value=AIProviderType.GEMINI), \
         patch("src.app.services.job_assistant.is_ai_available", return_value=True):
        from src.app.schemas_job_assistant import JobRequirement, MatchAnalysis, RequirementCategory, RequirementImportance
        mock_cloud.return_value = (
            [JobRequirement(text="Kubernetes", category=RequirementCategory.TECHNICAL_SKILL, importance=RequirementImportance.REQUIRED, raw_keyword="k8s")],
            MatchAnalysis(),
            [],
        )

        res1 = run_job_target_analysis(db, user.id, resume, job_input)
        assert mock_cloud.call_count == 1

        # Second call with identical input must hit cache
        res2 = run_job_target_analysis(db, user.id, resume, job_input)
        assert mock_cloud.call_count == 1
        assert res2.job_requirements[0].text == "Kubernetes"


def test_material_generation_caching_and_deduplication(test_db):
    """
    Generating an application material caches the result and deduplicates concurrent in-flight requests.
    """
    db, user, resume = test_db
    req = RegenerateMaterialRequest(
        material_type=MaterialType.COLD_EMAIL,
        target_role="Lead Architect",
        job_description="Architecting microservices on AWS with FastAPI, Docker, and Kubernetes.",
        language=SupportedLanguage.EN,
    )

    mock_json = '{"cold_email": {"subject": "Intro", "body": "Hello recruiter", "placeholders": ["[COMPANY]"]}}'

    with patch("src.app.services.job_assistant.generate_completion", return_value=mock_json) as mock_gen, \
         patch("src.app.services.job_assistant.get_active_provider", return_value=AIProviderType.GEMINI), \
         patch("src.app.services.job_assistant.is_ai_available", return_value=True):

        mat1 = regenerate_single_material(db, user.id, resume, req)
        assert mat1.generated is True
        assert mat1.subject == "Intro"
        assert mock_gen.call_count == 1

        # Second call should use cache
        mat2 = regenerate_single_material(db, user.id, resume, req)
        assert mat2.generated is True
        assert mock_gen.call_count == 1


def test_rate_limit_surfaces_retry_after(test_db):
    """
    On a Gemini 429 RESOURCE_EXHAUSTED error, regenerate_single_material must:
    - NOT retry automatically
    - Capture the retry_after_seconds from AIRateLimitError
    - Return an ungenerated material with the clear provider error and retry delay.
    """
    db, user, resume = test_db
    req = RegenerateMaterialRequest(
        material_type=MaterialType.SHORT_MESSAGE,
        target_role="VP of Engineering",
        job_description="Strategic engineering leadership for global distributed engineering teams.",
        language=SupportedLanguage.EN,
    )

    rate_limit_err = AIRateLimitError(
        "Google Gemini quota or rate limit exceeded. Please try again in ~2626s.",
        retry_after_seconds=2626.0,
    )

    with patch("src.app.services.job_assistant.generate_completion", side_effect=rate_limit_err) as mock_gen, \
         patch("src.app.services.job_assistant.get_active_provider", return_value=AIProviderType.GEMINI), \
         patch("src.app.services.job_assistant.is_ai_available", return_value=True):

        # Clear cache for this material
        _MATERIAL_CACHE.clear()

        mat = regenerate_single_material(db, user.id, resume, req)

        assert mat.generated is False
        assert "Google Gemini quota or rate limit exceeded" in mat.error
        assert mat.retry_after_seconds == 2626.0
        # Assert NO automatic retry loop burned duplicate requests
        assert mock_gen.call_count == 1
