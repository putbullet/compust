from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job, User, Resume, JobSkill
from src.app.security import create_access_token


@pytest.fixture
def tailor_test_env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        country = Country(id=1, name="Morocco", code="MA")
        company = Company(id=1, name="SecureCloud", website_url="https://securecloud.com", active=True)
        session.add_all([country, company])
        session.flush()

        user = User(
            id=1,
            email="candidate@compust.ai",
            password_hash="pw",
            is_active=True,
            first_name="Amine",
            last_name="El Amrani",
            created_at=now,
            updated_at=now,
        )
        session.add(user)

        job = Job(
            id=101,
            company_id=1,
            country_id=1,
            title="Senior Cybersecurity Architect",
            job_url="https://securecloud.com/jobs/101",
            description="Looking for Python, Linux, and Kubernetes specialist to secure infrastructure.",
            active=True,
            discovered_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        session.flush()

        # Explicit job skills
        session.add(JobSkill(job_id=101, skill="Python"))
        session.add(JobSkill(job_id=101, skill="Linux"))
        session.add(JobSkill(job_id=101, skill="Kubernetes"))
        session.add(JobSkill(job_id=101, skill="Terraform"))  # Candidate does not have this

        master_resume = Resume(
            id=50,
            user_id=1,
            title="General Master Resume",
            is_active=True,
            is_default=True,
            structured_data={
                "profile": {
                    "full_name": "Amine El Amrani",
                    "headline": "Full-Stack Software Engineer",
                    "email": "candidate@compust.ai",
                    "summary": "Experienced engineer with a focus on web systems and Python backend services.",
                },
                "skills": [
                    {"id": "sk1", "name": "Python", "category": "Backend", "proficiency": "Expert"},
                    {"id": "sk2", "name": "Linux", "category": "OS", "proficiency": "Advanced"},
                    {"id": "sk3", "name": "Docker", "category": "DevOps", "proficiency": "Intermediate"},
                ],
                "experience": [
                    {
                        "id": "exp1",
                        "company": "Alpha Tech",
                        "title": "Senior Engineer",
                        "description": "Maintained core infrastructure and backends.",
                        "highlights": ["Built internal deployment automation"],
                    }
                ],
                "education": [],
                "projects": [],
                "certifications": [],
                "languages": [],
                "custom_sections": [],
            },
            settings={"template": "modern", "theme_color": "#2563eb"},
            created_at=now,
            updated_at=now,
        )
        session.add(master_resume)
        session.commit()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    token = create_access_token({"sub": "1"})

    yield client, token
    app.dependency_overrides.clear()


def test_structured_ai_tailoring_suggestions(tailor_test_env):
    client, token = tailor_test_env
    headers = {"Authorization": f"Bearer {token}"}

    # Request tailoring suggestions for Job 101 with Master Resume 50
    resp = client.get("/api/v1/jobs/101/resumes/50/tailor", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["job_id"] == 101
    assert data["base_resume_id"] == 50
    assert data["base_resume_title"] == "General Master Resume"
    assert data["match_score"] > 0

    # Verify skills alignment
    assert "Python" in data["skills_to_emphasize"]
    assert "Linux" in data["skills_to_emphasize"]
    # Terraform is missing from candidate profile -> truthfully flagged as missing
    assert "Terraform" in data["missing_job_skills"]

    # Verify summary suggestion
    assert data["summary"]["original"] == "Experienced engineer with a focus on web systems and Python backend services."
    assert "Senior Cybersecurity Architect" in data["summary"]["suggested"]
    assert "Python" in data["summary"]["suggested"]

    # Verify experience refinements suggest highlights for existing experience only
    assert len(data["experience_refinements"]) >= 1
    assert data["experience_refinements"][0]["company"] == "Alpha Tech"


def test_save_tailored_copy_is_non_destructive(tailor_test_env):
    client, token = tailor_test_env
    headers = {"Authorization": f"Bearer {token}"}

    # Verify master resume state before tailoring
    master_before = client.get("/api/v1/resumes/50", headers=headers).json()
    orig_summary = master_before["structured_data"]["profile"]["summary"]
    orig_title = master_before["title"]

    # Save a tailored copy
    save_resp = client.post(
        "/api/v1/jobs/101/resumes/50/tailor/save-copy",
        headers=headers,
        json={
            "title": "Cybersecurity Architect — SecureCloud Tailored",
            "apply_suggested_summary": True,
            "apply_emphasized_skills": True,
            "accepted_experience_refinements": ["exp1"],
        },
    )
    assert save_resp.status_code == 200, save_resp.text
    tailored = save_resp.json()

    # The new resume is a distinct record
    assert tailored["id"] != 50
    assert tailored["title"] == "Cybersecurity Architect — SecureCloud Tailored"
    assert tailored["target_job_id"] == 101
    assert tailored["source_resume_id"] == 50
    assert tailored["is_default"] is False

    # The new resume has the tailored summary applied
    assert "Senior Cybersecurity Architect" in tailored["structured_data"]["profile"]["summary"]

    # CRITICAL: Verify the original master resume is completely UNCHANGED
    master_after = client.get("/api/v1/resumes/50", headers=headers).json()
    assert master_after["title"] == orig_title
    assert master_after["structured_data"]["profile"]["summary"] == orig_summary
    assert master_after["target_job_id"] is None
    assert master_after["is_default"] is True
