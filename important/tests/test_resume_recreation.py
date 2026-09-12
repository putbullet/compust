import io
from pathlib import Path
from datetime import datetime, timezone
import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job, User, Resume, CustomizedResume
from src.app.services.resume_recreator import (
    render_pdf_resume,
    render_docx_resume,
    validate_generated_resume_pdf,
    recreate_customized_resume_for_job,
    ResumeValidationError,
)


@pytest.fixture
def resume_env(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        country = Country(id=1, name="Morocco", code="MA")
        company = Company(id=1, name="TechCorp", website_url="https://techcorp.com", active=True)
        session.add_all([country, company])
        session.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
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
        job = Job(
            id=42,
            company_id=1,
            country_id=1,
            title="Senior Python Architect",
            job_url="https://techcorp.com/jobs/42",
            description="Seeking Python, FastAPI, Docker, and AWS architect with 5+ years experience.",
            active=True,
            discovered_at=now,
            created_at=now,
            updated_at=now,
        )
        resume = Resume(
            id=1,
            user_id=1,
            filename="Amine_CV.pdf",
            raw_text="Amine El Amrani. Software Engineer with Python and Docker background. Experience: Built scalable web microservices.",
            parsed_sections={
                "summary": "Seasoned Python Architect specialized in high-concurrency distributed systems.",
                "skills": ["Python", "FastAPI", "Docker", "AWS"],
                "experience": "Lead Developer at CloudSys (2021-2025)\n• Architected containerized microservices handling 50k req/min.",
                "education": "M.S. in Computer Science - EMI Rabat (2020)",
            },
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add_all([user, job, resume])
        session.commit()

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    yield session_factory, client, tmp_path

    app.dependency_overrides.clear()


def test_render_pdf_and_docx_rendering(resume_env):
    _, _, tmp_path = resume_env
    pdf_dest = tmp_path / "tailored_resume.pdf"
    docx_dest = tmp_path / "tailored_resume.docx"

    # Mock job
    class DummyJob:
        title = "Cloud Infrastructure Lead"

    sections = {
        "summary": "Seasoned Python Architect specialized in high-concurrency distributed systems.",
        "skills": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL"],
        "experience": "Lead Developer at CloudSys (2021-2025)\n• Architected containerized microservices handling 50k req/min.\n• Reduced latency by 35% through Redis caching.",
        "education": "M.S. in Software Engineering - ENSIAS (2020)",
    }

    # Render PDF
    render_pdf_resume(pdf_dest, "Amine El Amrani", sections, DummyJob())
    assert pdf_dest.exists()
    assert pdf_dest.stat().st_size > 500

    # Validate PDF extractability
    validate_generated_resume_pdf(pdf_dest)
    reader = PdfReader(str(pdf_dest))
    extracted = "".join(p.extract_text() for p in reader.pages)
    assert "Amine El Amrani" in extracted
    assert "Cloud Infrastructure Lead" in extracted
    assert "CloudSys" in extracted

    # Render DOCX
    render_docx_resume(docx_dest, "Amine El Amrani", sections, DummyJob())
    assert docx_dest.exists()
    assert docx_dest.stat().st_size > 500

    # Read DOCX back
    doc = Document(str(docx_dest))
    full_docx_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Amine El Amrani" in full_docx_text
    assert "Cloud Infrastructure Lead" in full_docx_text
    assert "PROFESSIONAL EXPERIENCE" in full_docx_text


def test_recreate_resume_service(resume_env):
    session_factory, _, _ = resume_env

    with session_factory() as session:
        job = session.query(Job).filter(Job.id == 42).first()
        resume = session.query(Resume).filter(Resume.user_id == 1).first()

        customized = recreate_customized_resume_for_job(
            db=session,
            user_id=1,
            base_resume=resume,
            job=job,
            user_name="Amine El Amrani",
        )

        assert customized is not None
        assert customized.version == 1
        assert customized.pdf_filename is not None
        assert customized.docx_filename is not None
        assert len(customized.recommendations or []) >= 0

        # Second creation increments version
        customized_v2 = recreate_customized_resume_for_job(
            db=session,
            user_id=1,
            base_resume=resume,
            job=job,
            user_name="Amine El Amrani",
        )
        assert customized_v2.version == 2


def test_resume_customization_api_flow(resume_env):
    session_factory, client, _ = resume_env

    # Register candidate
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "amine@compust.ai", "password": "SecurePassword123!"},
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Associate existing resume to this new registered user id
    with session_factory() as session:
        new_user = session.query(User).filter(User.email == "amine@compust.ai").first()
        res = session.query(Resume).filter(Resume.id == 1).first()
        res.user_id = new_user.id
        session.commit()

    # Call recreate endpoint
    recreate_res = client.post(
        "/api/v1/jobs/42/resume-customizations/recreate",
        headers=headers,
    )
    assert recreate_res.status_code == 200
    data = recreate_res.json()
    assert data["job_id"] == 42
    assert data["version"] == 1
    custom_id = data["id"]

    # Download PDF
    pdf_dl = client.get(f"/api/v1/customized-resumes/{custom_id}/download/pdf", headers=headers)
    assert pdf_dl.status_code == 200
    assert pdf_dl.headers["content-type"] == "application/pdf"
    assert len(pdf_dl.content) > 100

    # Download DOCX
    docx_dl = client.get(f"/api/v1/customized-resumes/{custom_id}/download/docx", headers=headers)
    assert docx_dl.status_code == 200
    assert "wordprocessingml" in docx_dl.headers["content-type"]
    assert len(docx_dl.content) > 100

    # Get history
    history_res = client.get("/api/v1/jobs/42/customized-resumes", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()) >= 1
