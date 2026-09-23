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
from src.app.models import Base, User, Resume
from src.app.schemas_resume import (
    DEFAULT_SECTION_TITLES,
    resolve_section_title,
    ResumeSettings,
)
from src.app.security import create_access_token
from src.app.services.resume_export import render_template_docx, render_template_pdf


# ---------------------------------------------------------------------------
# Unit tests for title resolution
# ---------------------------------------------------------------------------

def test_resolve_section_title_defaults():
    assert resolve_section_title("experience") == "Professional Experience"
    assert resolve_section_title("education") == "Education & Academic Background"
    assert resolve_section_title("skills") == "Technical & Core Skills"
    assert resolve_section_title("summary") == "Professional Summary"
    assert resolve_section_title("projects") == "Featured Projects"
    assert resolve_section_title("certifications") == "Certifications & Accreditations"
    assert resolve_section_title("languages") == "Languages"
    assert resolve_section_title("custom_sections") == "Additional Information"


def test_resolve_section_title_custom():
    assert resolve_section_title("experience", "Work History") == "Work History"
    assert resolve_section_title("experience", "Expérience Professionnelle") == "Expérience Professionnelle"
    assert resolve_section_title("skills", "Compétences Techniques") == "Compétences Techniques"
    assert resolve_section_title("education", "Berufsausbildung") == "Berufsausbildung"


def test_resolve_section_title_whitespace_fallback():
    # Empty string falls back to default
    assert resolve_section_title("experience", "") == "Professional Experience"
    # Whitespace only falls back to default
    assert resolve_section_title("experience", "   ") == "Professional Experience"
    assert resolve_section_title("skills", "\t\n  ") == "Technical & Core Skills"
    # None falls back to default
    assert resolve_section_title("education", None) == "Education & Academic Background"


def test_resume_settings_backward_compatibility():
    # Settings initialized without section_titles works seamlessly
    settings = ResumeSettings()
    assert settings.section_titles == {}
    assert resolve_section_title("experience", settings.section_titles.get("experience")) == "Professional Experience"


# ---------------------------------------------------------------------------
# PDF and DOCX Export with Custom and Default Titles
# ---------------------------------------------------------------------------

@pytest.fixture
def resume_test_env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
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
        session.add(user)
        session.flush()

        resume_french = Resume(
            id=10,
            user_id=1,
            title="French Tailored Resume",
            is_active=True,
            is_default=True,
            structured_data={
                "profile": {
                    "full_name": "Amine El Amrani",
                    "headline": "Lead Solutions Architect",
                    "email": "candidate@compust.ai",
                    "summary": "Architecte logiciel avec 10+ ans d'expérience.",
                },
                "skills": [
                    {"id": "s1", "name": "Python", "category": "Backend", "proficiency": "Expert"},
                ],
                "experience": [
                    {
                        "id": "e1",
                        "company": "Cloud Systems",
                        "title": "Principal Architect",
                        "start_date": "2020-01",
                        "end_date": "Present",
                        "is_current": True,
                        "description": "Architecte cloud et systèmes distribués.",
                    }
                ],
                "education": [
                    {
                        "id": "ed1",
                        "institution": "ENSEIRB-MATMECA",
                        "degree": "Diplôme d'ingénieur",
                        "field": "Télécommunications",
                        "start_date": "2015",
                        "end_date": "2018",
                    }
                ],
            },
            settings={
                "template": "modern",
                "theme_color": "#2563eb",
                "font_family": "Inter",
                "font_size": "10.5",
                "document_size": "A4",
                "section_titles": {
                    "summary": "Profil & Objectifs",
                    "experience": "Expérience Professionnelle",
                    "education": "Formation & Diplômes",
                    "skills": "Compétences Clés",
                },
            },
            created_at=now,
            updated_at=now,
        )

        # Existing resume from old schema without section_titles field
        resume_legacy = Resume(
            id=20,
            user_id=1,
            title="Legacy Resume Without Custom Titles",
            is_active=True,
            is_default=False,
            structured_data={
                "profile": {
                    "full_name": "Amine El Amrani",
                    "summary": "Experienced engineer.",
                },
                "skills": [{"id": "s1", "name": "Python"}],
                "experience": [{"id": "e1", "company": "Tech Corp", "title": "Developer"}],
            },
            settings={
                "template": "classic",
                "theme_color": "#2563eb",
                "font_family": "Inter",
                "font_size": "10.5",
                "document_size": "A4",
                # No section_titles key present!
            },
            created_at=now,
            updated_at=now,
        )

        session.add_all([resume_french, resume_legacy])
        session.commit()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    token = create_access_token({"sub": "1"})

    yield client, token
    app.dependency_overrides.clear()


def test_export_pdf_with_multilingual_custom_titles(resume_test_env, tmp_path):
    client, token = resume_test_env
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/resumes/10/export/pdf", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"

    reader = PdfReader(io.BytesIO(resp.content))
    total_text = "".join(page.extract_text() or "" for page in reader.pages)
    upper_text = total_text.upper()

    # Assert custom French titles appear (case-insensitive for RenderCV / ReportLab compatibility)
    assert "EXPÉRIENCE PROFESSIONNELLE" in upper_text
    assert "FORMATION & DIPLÔMES" in upper_text
    assert "COMPÉTENCES CLÉS" in upper_text
    assert "PROFIL & OBJECTIFS" in upper_text


def test_export_docx_with_multilingual_custom_titles(resume_test_env):
    client, token = resume_test_env
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/resumes/10/export/docx", headers=headers)
    assert resp.status_code == 200

    doc = Document(io.BytesIO(resp.content))
    paragraphs_text = "\n".join(p.text for p in doc.paragraphs).upper()

    assert "EXPÉRIENCE PROFESSIONNELLE" in paragraphs_text
    assert "FORMATION & DIPLÔMES" in paragraphs_text
    assert "COMPÉTENCES CLÉS" in paragraphs_text


def test_legacy_resume_backward_compatibility_pdf(resume_test_env):
    client, token = resume_test_env
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/resumes/20/export/pdf", headers=headers)
    assert resp.status_code == 200

    reader = PdfReader(io.BytesIO(resp.content))
    total_text = "".join(page.extract_text() or "" for page in reader.pages)
    upper_text = total_text.upper()

    # Legacy resume has no custom titles -> must default gracefully without error
    assert "PROFESSIONAL EXPERIENCE" in upper_text or "PROFESSIONAL TENURE" in upper_text
    assert "TECHNICAL & CORE SKILLS" in upper_text


def test_update_resume_section_titles_via_api(resume_test_env):
    client, token = resume_test_env
    headers = {"Authorization": f"Bearer {token}"}

    # Update with German custom titles
    update_payload = {
        "settings": {
            "template": "modern",
            "section_titles": {
                "experience": "Berufserfahrung",
                "skills": "Fachliche Fähigkeiten",
                "summary": "   ",  # Whitespace only -> should fallback
            },
        }
    }

    put_resp = client.put("/api/v1/resumes/10", headers=headers, json=update_payload)
    assert put_resp.status_code == 200
    res_data = put_resp.json()
    assert res_data["settings"]["section_titles"]["experience"] == "Berufserfahrung"

    # Export PDF and verify
    pdf_resp = client.get("/api/v1/resumes/10/export/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    reader = PdfReader(io.BytesIO(pdf_resp.content))
    total_text = "".join(page.extract_text() or "" for page in reader.pages)
    upper_text = total_text.upper()

    assert "BERUFSERFAHRUNG" in upper_text
    assert "FACHLICHE FÄHIGKEITEN" in upper_text
    # Whitespace fallback should display default "PROFESSIONAL SUMMARY"
    assert "PROFESSIONAL SUMMARY" in upper_text
