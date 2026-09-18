"""
test_live_ollama_integration.py
================================
Live integration test for Ollama with local model (e.g. qwen3.5:0.8b).
Skipped automatically if Ollama is not running or no model is available.
"""
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.models import Base, User, Resume
from src.app.schemas_job_assistant import ExternalJobInput, SupportedLanguage
from src.app.services.ai_service import check_ollama_runtime, generate_completion
from src.app.services.job_assistant import run_job_target_analysis


@pytest.fixture
def is_ollama_ready():
    status = check_ollama_runtime()
    if status["status"] != "connected" or not status.get("models"):
        pytest.skip("Local Ollama is not connected or has no installed models.")
    return status


def test_ollama_generate_with_think_false(is_ollama_ready):
    """Verify that generate_completion with think: False returns non-empty structured text quickly."""
    resp = generate_completion(
        prompt="Return valid JSON: {\"status\": \"ready\", \"engine\": \"ollama\"}",
        system_prompt="You are a precise assistant. Return ONLY valid JSON.",
        temperature=0.1,
        timeout_seconds=30.0,
    )
    assert resp, "Response from Ollama should not be empty"
    assert "ready" in resp or "status" in resp


def test_live_job_target_pipeline(is_ollama_ready):
    """Verify the full 4-stage pipeline executes with the live local model."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    with factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user = User(
            id=1, email="test_live@compust.ai", password_hash="hash",
            is_active=True, first_name="Mehdi", last_name="Bennani",
            created_at=now, updated_at=now,
        )
        session.add(user)

        resume = Resume(
            id=100, user_id=1, title="Master Developer Resume",
            is_active=True, is_default=True,
            structured_data={
                "profile": {
                    "full_name": "Mehdi Bennani",
                    "headline": "Full-Stack Security Developer",
                    "email": "test_live@compust.ai",
                    "summary": "Software developer with 2 years of Python and Docker experience.",
                },
                "skills": [
                    {"id": "s1", "name": "Python", "proficiency": "Expert"},
                    {"id": "s2", "name": "Docker", "proficiency": "Intermediate"},
                    {"id": "s3", "name": "FastAPI", "proficiency": "Intermediate"},
                ],
                "experience": [
                    {
                        "id": "e1", "title": "Developer Intern", "company": "TechNorth",
                        "description": "Built automated Python microservices and Docker containers.",
                        "start_date": "2023-01", "end_date": "2023-08",
                    }
                ],
                "education": [
                    {"id": "ed1", "institution": "INPT", "degree": "BSc", "field": "Software Engineering"}
                ],
                "projects": [
                    {"id": "p1", "name": "PhiGuard", "description": "Phishing detection with Python", "technologies": "Python, FastAPI"}
                ],
                "languages": [{"id": "l1", "language": "English", "proficiency": "Fluent"}],
                "certifications": [],
            },
            created_at=now, updated_at=now,
        )
        session.add(resume)
        session.commit()

        job_input = ExternalJobInput(
            target_role="Cybersecurity Software Engineer Intern",
            job_description="""
We are seeking a Cybersecurity Software Engineer Intern.
Requirements:
- Strong Python programming skills for building internal tooling and automation.
- Experience with Docker and containerization.
- Knowledge of REST APIs (FastAPI or Flask).
- Familiarity with security concepts, phishing analysis, or threat detection.
- English communication required.
            """,
            additional_information="Company: Orange Cyberdefense",
            language=SupportedLanguage.EN,
        )

        result = run_job_target_analysis(session, user.id, resume, job_input)
        assert result.resume_id == 100
        assert result.deterministic_score.overall > 0
        assert len(result.job_requirements) > 0
        assert len(result.resume_recommendations) > 0
        # Check master resume was not mutated in database
        refetched = session.get(Resume, 100)
        assert refetched.title == "Master Developer Resume"
        assert refetched.structured_data["profile"]["summary"] == "Software developer with 2 years of Python and Docker experience."
