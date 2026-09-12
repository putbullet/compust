from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job, User, Resume
from src.app.security import create_access_token


def test_frontend_ai_tailoring_is_disabled_and_shows_coming_soon():
    """Verify that JobDetailModal and ResumeTailorDrawer have AI tailoring disabled with 'coming soon' messaging."""
    repo_root = Path(__file__).resolve().parent.parent
    job_detail_modal_path = repo_root / "frontend" / "src" / "components" / "JobDetailModal.tsx"
    resume_tailor_drawer_path = repo_root / "frontend" / "src" / "components" / "ResumeBuilder" / "ResumeTailorDrawer.tsx"

    assert job_detail_modal_path.exists(), f"Missing {job_detail_modal_path}"
    assert resume_tailor_drawer_path.exists(), f"Missing {resume_tailor_drawer_path}"

    modal_content = job_detail_modal_path.read_text(encoding="utf-8")
    drawer_content = resume_tailor_drawer_path.read_text(encoding="utf-8")

    # 1. Coming soon message must be prominent
    assert "AI resume tailoring is coming soon" in modal_content
    assert "AI resume tailoring is coming soon" in drawer_content

    # 2. Tailoring action buttons must be disabled and not open drawer or trigger API calls
    assert "disabled" in modal_content
    assert 'aria-disabled="true"' in modal_content

    # 3. Normal CV recommendations must be preserved and wired
    assert "handleFetchResumeSuggestions" in modal_content
    assert "api.getResumeSuggestions" in modal_content
    assert "Suggest Resume Customization" in modal_content

    # 4. Tailor drawer must NOT invoke AI tailoring endpoints
    assert "api.getJobResumeTailorSuggestions" not in drawer_content
    assert "api.saveJobTailoredResumeCopy" not in drawer_content


def test_normal_cv_recommendations_endpoint_remains_active():
    """Verify backend resume suggestions and intelligence endpoints remain active and functional."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with session_factory() as session:
        user = User(
            id=42,
            email="test@compust.ai",
            password_hash="pw",
            is_active=True,
            first_name="Test",
            last_name="User",
            created_at=now,
            updated_at=now,
        )
        country = Country(id=1, name="Morocco", code="MA")
        company = Company(id=1, name="TechCorp", website_url="https://techcorp.com", active=True)
        job = Job(
            id=10,
            company_id=1,
            country_id=1,
            title="Senior Python Engineer",
            job_url="https://example.com/job/10",
            description="Need Python, FastAPI, Docker, and PostgreSQL expertise.",
            active=True,
            discovered_at=now,
            created_at=now,
            updated_at=now,
        )
        resume = Resume(
            id=1,
            user_id=42,
            title="Senior Engineer CV",
            raw_text="Experienced Python software engineer with FastAPI experience.",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add_all([user, country, company, job, resume])
        session.commit()

    token = create_access_token(data={"sub": "test@compust.ai"})
    client = TestClient(app)

    # Calling normal CV suggestions endpoint must succeed with status 200
    response = client.post(
        "/api/v1/jobs/10/resume-suggestions",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_title" in data
    assert "already_demonstrated" in data
    assert "missing_or_weak" in data

    app.dependency_overrides.clear()
