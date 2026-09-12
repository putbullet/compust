"""
Deep verification of resume download payloads and document validity.
Verifies:
- HTTP 200 with correct Content-Type (application/pdf, OOXML wordprocessingml)
- Proper Content-Disposition header with clean .pdf / .docx filename
- Response body is genuine binary PDF / DOCX, NOT JSON, NOT HTML, NOT SVG
- PDF is parseable by pypdf and has valid page count and text
- DOCX is parseable by python-docx and has valid OOXML structure
- Full security: 401 unauthenticated, 404 cross-user boundary, 404 invalid ID
"""

import io
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
from src.app.models import Base, Company, CustomizedResume, Job, Resume, User
from src.app.security import create_access_token, hash_password
from src.app.services.resume_recreator import STORAGE_DIR


@pytest.fixture
def payload_test_setup():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSession()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    u1 = User(
        email="candidate1@example.com",
        password_hash=hash_password("secret123"),
        first_name="Alice",
        last_name="Candidate",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    u2 = User(
        email="candidate2@example.com",
        password_hash=hash_password("secret123"),
        first_name="Bob",
        last_name="Unauthorized",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add_all([u1, u2])
    db.commit()
    db.refresh(u1)
    db.refresh(u2)

    from src.app.models import Country
    country = Country(name="Morocco", code="MA")
    db.add(country)
    db.commit()
    db.refresh(country)

    comp = Company(name="Capgemini Maroc", website_url="https://capgemini.ma", active=True)
    db.add(comp)
    db.commit()
    db.refresh(comp)

    job = Job(
        company_id=comp.id,
        country_id=country.id,
        title="Full Stack Software Engineer",
        job_url="https://capgemini.ma/careers/full-stack-123",
        description="Looking for Python, React, and AWS experience in Casablanca.",
        location="Casablanca, Morocco",
        active=True,
        discovered_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    base_res = Resume(
        user_id=u1.id,
        filename="alice_original.pdf",
        raw_text="Alice Candidate. 5 years Python and React development.",
        parsed_sections={
            "summary": "Experienced Full Stack Engineer passionate about cloud and frontend architecture.",
            "skills": ["Python", "React", "Docker", "AWS", "SQL"],
            "experience": "- Senior Software Developer at Tech Corp\n- Built scalable microservices",
            "education": "BS in Computer Science",
        },
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(base_res)
    db.commit()
    db.refresh(base_res)

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_fname = f"resume_{u1.id}_job_{job.id}_test.pdf"
    docx_fname = f"resume_{u1.id}_job_{job.id}_test.docx"

    pdf_path = STORAGE_DIR / pdf_fname
    docx_path = STORAGE_DIR / docx_fname

    # Render actual documents using the application's renderers
    from src.app.services.resume_recreator import render_docx_resume, render_pdf_resume
    render_pdf_resume(pdf_path, "Alice Candidate", base_res.parsed_sections, job)
    render_docx_resume(docx_path, "Alice Candidate", base_res.parsed_sections, job)

    custom_res = CustomizedResume(
        user_id=u1.id,
        base_resume_id=base_res.id,
        job_id=job.id,
        version=1,
        pdf_filename=pdf_fname,
        docx_filename=docx_fname,
        raw_text=base_res.raw_text,
        parsed_sections=base_res.parsed_sections,
        created_at=now,
    )
    db.add(custom_res)
    db.commit()
    db.refresh(custom_res)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    u1_token = create_access_token(data={"sub": str(u1.id), "email": u1.email})
    u2_token = create_access_token(data={"sub": str(u2.id), "email": u2.email})

    class Context:
        pass

    ctx = Context()
    ctx.client = client
    ctx.u1 = u1
    ctx.u2 = u2
    ctx.u1_token = u1_token
    ctx.u2_token = u2_token
    ctx.custom_res = custom_res
    ctx.pdf_fname = pdf_fname
    ctx.docx_fname = docx_fname
    ctx.pdf_path = pdf_path
    ctx.docx_path = docx_path

    yield ctx

    app.dependency_overrides.clear()
    test_engine.dispose()
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception:
            pass
    if docx_path.exists():
        try:
            docx_path.unlink()
        except Exception:
            pass


def test_pdf_payload_is_valid_reportlab_pdf(payload_test_setup):
    """Verify downloaded PDF is true binary PDF, not HTML, not SVG, parseable by pypdf."""
    ctx = payload_test_setup
    # Test via query token (used by direct browser download)
    resp = ctx.client.get(
        f"/api/v1/customized-resumes/{ctx.custom_res.id}/download/pdf?token={ctx.u1_token}"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    disp = resp.headers.get("content-disposition", "")
    assert "attachment" in disp
    assert ctx.pdf_fname in disp

    content = resp.content
    assert len(content) > 500
    # Must start with %PDF- header
    assert content.startswith(b"%PDF-1.")
    # Must not be HTML, JSON, or SVG
    assert not content.startswith(b"<!DOCTYPE html>")
    assert not content.startswith(b"{")
    assert not content.startswith(b"<svg")

    # Validate with pypdf
    reader = PdfReader(io.BytesIO(content))
    assert len(reader.pages) >= 1
    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""
    assert "Alice Candidate" in extracted_text
    assert "Full Stack Software Engineer" in extracted_text


def test_docx_payload_is_valid_ooxml_document(payload_test_setup):
    """Verify downloaded DOCX is true OpenXML zip archive, parseable by python-docx."""
    ctx = payload_test_setup
    resp = ctx.client.get(
        f"/api/v1/customized-resumes/{ctx.custom_res.id}/download/docx?token={ctx.u1_token}"
    )
    assert resp.status_code == 200
    assert "wordprocessingml" in resp.headers["content-type"]
    disp = resp.headers.get("content-disposition", "")
    assert "attachment" in disp
    assert ctx.docx_fname in disp

    content = resp.content
    assert len(content) > 1000
    # Must start with ZIP header magic bytes PK\x03\x04
    assert content.startswith(b"PK\x03\x04")
    # Must not be HTML, JSON, or SVG
    assert not content.startswith(b"<!DOCTYPE html>")
    assert not content.startswith(b"{")
    assert not content.startswith(b"<svg")

    # Validate with python-docx
    doc = Document(io.BytesIO(content))
    paragraphs_text = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = " ".join(paragraphs_text)
    assert "Alice Candidate" in full_text
    assert "Full Stack Software Engineer" in full_text


def test_download_security_cross_user_isolation(payload_test_setup):
    """Verify user B cannot download user A's customized resume."""
    ctx = payload_test_setup
    resp = ctx.client.get(
        f"/api/v1/customized-resumes/{ctx.custom_res.id}/download/pdf?token={ctx.u2_token}"
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_download_unauthenticated_rejected(payload_test_setup):
    """Verify unauthenticated request without token is rejected with 401."""
    ctx = payload_test_setup
    resp = ctx.client.get(f"/api/v1/customized-resumes/{ctx.custom_res.id}/download/pdf")
    assert resp.status_code == 401


def test_download_nonexistent_resume_returns_404(payload_test_setup):
    """Verify requesting non-existent resume ID returns 404."""
    ctx = payload_test_setup
    resp = ctx.client.get(
        f"/api/v1/customized-resumes/99999/download/pdf?token={ctx.u1_token}"
    )
    assert resp.status_code == 404
