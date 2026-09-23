"""Tests for Resume Studio ATS Checker."""

import json
import pytest
from unittest.mock import patch

from src.app.services.ats_checker import (
    calculate_deterministic_ats_score,
    evaluate_resume_ats,
    _extract_json_block,
    ATSCheckResult,
)
from src.app.services.ai_service import OllamaUnavailableError


WEAK_RESUME_TEXT = """
Jane Doe
Summary: Hard worker looking for a job.
Experience:
Worked at ABC Company.
Responsible for daily tasks and helping team.
Education:
High School.
"""

STRONG_RESUME_TEXT = """
Alexandre Martin
alexandre.martin@example.com | +33 6 12 34 56 78 | Paris, France | https://linkedin.com/in/alexmartin

Summary
Senior Software Architect with 8+ years designing high-throughput distributed systems in Python and React.

Expérience Professionnelle
Staff Software Engineer — TechCorp (2021 – Present)
- Architected and scaled real-time microservices handling over 50,000 requests/sec with 99.99% uptime.
- Optimized PostgreSQL database queries, reducing p99 latency by 45% and saving $120,000 annually.
- Spearheaded CI/CD migration to Docker and Kubernetes, accelerating deployment velocity by 3x.
- Mentored a team of 8 junior and mid-level software engineers.

Lead Developer — DataScale (2018 – 2021)
- Developed asynchronous data ingestion pipelines processing 5M events daily using Python and Kafka.
- Refactored core payment gateway integration, decreasing checkout transaction failures by 60%.

Formation
Master of Science in Computer Science — Sorbonne Université (2018)

Compétences
Python, React, TypeScript, PostgreSQL, Docker, Kubernetes, AWS, FastAPI, CI/CD, Git, Microservices
"""


def test_deterministic_weak_resume():
    result = calculate_deterministic_ats_score(
        resume_text=WEAK_RESUME_TEXT,
        role="Senior Backend Engineer",
        field="Software Engineering",
    )
    assert isinstance(result, ATSCheckResult)
    assert result.provider == "deterministic"
    assert result.overall_score < 60  # Weak resume should fail or need heavy optimization
    assert result.verdict in ("Needs Optimization", "High ATS Rejection Risk")

    # Should flag missing contact (email, phone), missing metrics, and missing skills section
    categories_by_key = {c.category: c for c in result.categories}
    assert categories_by_key["impact"].score < 50
    assert categories_by_key["contact"].score < 50
    assert any(f.severity == "critical" for f in result.feedback)


def test_deterministic_strong_multilingual_resume():
    result = calculate_deterministic_ats_score(
        resume_text=STRONG_RESUME_TEXT,
        role="Software Engineer",
        field="Backend",
    )
    assert isinstance(result, ATSCheckResult)
    assert result.provider == "deterministic"
    assert result.overall_score >= 80
    assert result.verdict in ("Strong Match", "Competitive")

    categories_by_key = {c.category: c for c in result.categories}
    # Section standardization must recognize French "Expérience Professionnelle", "Formation", "Compétences"
    assert categories_by_key["sections"].status == "pass"
    assert categories_by_key["contact"].status == "pass"
    assert categories_by_key["impact"].status == "pass"

    # Action verbs and metrics detected
    assert len(result.keywords_found) > 0


def test_json_block_extraction():
    raw_wrapped = "Here is your analysis:\n```json\n{\"overall_score\": 88, \"verdict\": \"Competitive\"}\n```\nHope this helps!"
    assert _extract_json_block(raw_wrapped) == '{"overall_score": 88, "verdict": "Competitive"}'

    raw_unfenced = "Some prefix { \"key\": 123 } some suffix"
    assert _extract_json_block(raw_unfenced) == '{ "key": 123 }'


def test_evaluate_resume_ats_fallback_when_ollama_fails():
    with patch("src.app.services.ats_checker.generate_completion", side_effect=OllamaUnavailableError("No connection")):
        result = evaluate_resume_ats(
            resume_text=STRONG_RESUME_TEXT,
            role="Software Engineer",
            field="Technology",
            use_llm=True,
        )
        assert result.provider == "deterministic"
        assert result.overall_score >= 80


def test_evaluate_resume_ats_with_mocked_ollama():
    mock_payload = {
        "overall_score": 92,
        "verdict": "Strong Match",
        "categories": [
            {"category": "parseability", "name": "ATS Parseability & Hygiene", "score": 95, "max_score": 100, "status": "pass", "notes": "Clean."},
            {"category": "keywords", "name": "Keyword & Competency Alignment", "score": 90, "max_score": 100, "status": "pass", "notes": "Aligned."},
            {"category": "sections", "name": "Section Standardization", "score": 95, "max_score": 100, "status": "pass", "notes": "Standard."},
            {"category": "impact", "name": "Quantifiable Impact & Verbs", "score": 90, "max_score": 100, "status": "pass", "notes": "Strong metrics."},
            {"category": "formatting", "name": "Formatting & Layout Norms", "score": 90, "max_score": 100, "status": "pass", "notes": "Clean."},
            {"category": "contact", "name": "Contact Detectability", "score": 95, "max_score": 100, "status": "pass", "notes": "All present."}
        ],
        "feedback": [
            {
                "id": "fb1",
                "category": "impact",
                "severity": "pass",
                "title": "Strong Quantitative Results",
                "message": "Excellent use of metrics ($120k, 50k req/s).",
                "recommendation": "Maintain this metric rigor.",
                "grounded_quote": "reducing p99 latency by 45%"
            }
        ],
        "keywords_found": ["Python", "Docker", "Kubernetes", "PostgreSQL"],
        "keywords_missing": ["Terraform"],
        "recommended_action_verbs": ["Spearheaded", "Architected"]
    }

    with patch("src.app.services.ats_checker.generate_completion", return_value=f"```json\n{json.dumps(mock_payload)}\n```"):
        result = evaluate_resume_ats(
            resume_text=STRONG_RESUME_TEXT,
            role="Software Engineer",
            use_llm=True,
        )
        assert result.provider == "ollama"
        assert result.overall_score == 92
        assert result.verdict == "Strong Match"
from datetime import datetime, timezone
from src.app.models import User, Resume
from src.app.security import create_access_token, hash_password


@pytest.fixture
def auth_user(db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = User(
        email="ats_candidate@compust.ma",
        password_hash=hash_password("Password123!"),
        first_name="Jane",
        last_name="Doe",
        is_active=True,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(auth_user):
    token = create_access_token({"sub": str(auth_user.id), "email": auth_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def active_resume(db_session, auth_user):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    resume = Resume(
        user_id=auth_user.id,
        title="Jane Doe CV",
        filename="jane_doe_cv.pdf",
        raw_text=STRONG_RESUME_TEXT,
        structured_data={
            "profile": {
                "full_name": "Alexandre Martin",
                "headline": "Staff Software Engineer",
                "email": "alexandre.martin@example.com",
                "phone": "+33 6 12 34 56 78",
                "location": "Paris, France",
            },
            "experience": [
                {
                    "title": "Staff Software Engineer",
                    "company": "TechCorp",
                    "bullets": ["Architected distributed systems handling 50k req/s."],
                }
            ],
            "education": [
                {
                    "degree": "Master of Science",
                    "institution": "Sorbonne Université",
                }
            ],
            "skills": [
                {"name": "Python"},
                {"name": "Docker"},
            ],
        },
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


def test_ats_checker_endpoint(client, auth_headers, active_resume):
    payload = {
        "target_role": "Backend Architect",
        "target_field": "Cloud Computing",
    }
    response = client.post(
        f"/api/v1/resumes/{active_resume.id}/ats-check",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "verdict" in data
    assert "categories" in data
    assert len(data["categories"]) == 6
    assert "feedback" in data
    assert data["provider"] in ("ollama", "deterministic")

