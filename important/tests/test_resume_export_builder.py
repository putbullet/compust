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
from src.app.security import create_access_token


@pytest.fixture
def export_test_env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user1 = User(
            id=1,
            email="candidate@compust.ai",
            password_hash="pw",
            is_active=True,
            first_name="Amine",
            last_name="El Amrani",
            created_at=now,
            updated_at=now,
        )
        user2 = User(
            id=2,
            email="other@compust.ai",
            password_hash="pw",
            is_active=True,
            first_name="Other",
            last_name="User",
            created_at=now,
            updated_at=now,
        )
        session.add_all([user1, user2])
        session.flush()

        resume1 = Resume(
            id=10,
            user_id=1,
            title="Lead Architecture Resume",
            is_active=True,
            is_default=True,
            structured_data={
                "profile": {
                    "full_name": "Amine El Amrani",
                    "headline": "Lead Solutions Architect",
                    "email": "candidate@compust.ai",
                    "phone": "+212 600-112233",
                    "location": "Casablanca, Morocco",
                    "website": "https://amine.dev",
                    "github": "https://github.com/amine",
                    "linkedin": "https://linkedin.com/in/amine",
                    "summary": "Seasoned engineering leader with 10+ years architecting cloud platforms.",
                },
                "skills": [
                    {"id": "s1", "name": "Python", "category": "Backend", "proficiency": "Expert"},
                    {"id": "s2", "name": "FastAPI", "category": "Backend", "proficiency": "Expert"},
                    {"id": "s3", "name": "AWS", "category": "Cloud", "proficiency": "Advanced"},
                ],
                "experience": [
                    {
                        "id": "e1",
                        "company": "Enterprise Cloud Systems",
                        "title": "Principal Architect",
                        "location": "Casablanca",
                        "employment_type": "full_time",
                        "start_date": "2020-01",
                        "end_date": "Present",
                        "is_current": True,
                        "description": "Led architectural decisions for distributed high-load infrastructure.",
                        "highlights": ["Designed resilient event pipelines", "Reduced cloud expenditure by 28%"],
                    }
                ],
                "education": [
                    {
                        "id": "ed1",
                        "institution": "ENSEIRB-MATMECA",
                        "degree": "Master of Engineering",
                        "field": "Software & Telecommunications",
                        "location": "France",
                        "start_date": "2015",
                        "end_date": "2018",
                    }
                ],
                "projects": [
                    {
                        "id": "p1",
                        "name": "Distributed Search Engine",
                        "description": "High-concurrency search cluster with sub-millisecond query latency.",
                        "technologies": "Python, Redis, Elasticsearch",
                        "url": "https://github.com/amine/search",
                    }
                ],
                "certifications": [
                    {
                        "id": "c1",
                        "name": "AWS Certified Solutions Architect - Professional",
                        "issuer": "Amazon Web Services",
                        "issue_date": "2023-01",
                    }
                ],
                "languages": [
                    {"id": "l1", "language": "Arabic", "proficiency": "Native"},
                    {"id": "l2", "language": "French", "proficiency": "Fluent"},
                    {"id": "l3", "language": "English", "proficiency": "Fluent"},
                ],
                "custom_sections": [],
            },
            settings={
                "template": "modern",
                "theme_color": "#2563eb",
                "font_family": "Inter",
                "font_size": "10.5",
                "document_size": "A4",
            },
            created_at=now,
            updated_at=now,
        )
        session.add(resume1)
        session.commit()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    token1 = create_access_token({"sub": "1"})
    token2 = create_access_token({"sub": "2"})

    yield client, token1, token2
    app.dependency_overrides.clear()


@pytest.mark.parametrize("template", ["modern", "classic", "minimal", "technical"])
def test_export_pdf_all_templates_validity(export_test_env, template):
    client, token1, _ = export_test_env
    headers = {"Authorization": f"Bearer {token1}"}

    # Update template setting
    client.put(
        "/api/v1/resumes/10",
        headers=headers,
        json={"settings": {"template": template, "theme_color": "#0ea5e9", "font_size": "10.5", "document_size": "A4"}},
    )

    resp = client.get("/api/v1/resumes/10/export/pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert ".pdf" in resp.headers.get("content-disposition", "")

    # Validate actual binary PDF payload
    content = resp.content
    assert len(content) > 1000
    assert content.startswith(b"%PDF-")

    reader = PdfReader(io.BytesIO(content))
    assert len(reader.pages) >= 1
    total_text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Amine El Amrani" in total_text
    assert "Enterprise Cloud Systems" in total_text
    assert "Python" in total_text


@pytest.mark.parametrize("template", ["modern", "classic", "minimal", "technical"])
def test_export_docx_all_templates_validity(export_test_env, template):
    client, token1, _ = export_test_env
    headers = {"Authorization": f"Bearer {token1}"}

    client.put(
        "/api/v1/resumes/10",
        headers=headers,
        json={"settings": {"template": template, "theme_color": "#10b981", "font_size": "10.5", "document_size": "A4"}},
    )

    resp = client.get("/api/v1/resumes/10/export/docx", headers=headers)
    assert resp.status_code == 200, resp.text
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert ".docx" in resp.headers.get("content-disposition", "")

    # Validate actual OOXML DOCX document
    content = resp.content
    assert len(content) > 1000
    doc = Document(io.BytesIO(content))
    paragraphs_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Amine El Amrani" in paragraphs_text
    assert "Enterprise Cloud Systems" in paragraphs_text
    assert "Python" in paragraphs_text


def test_export_security_isolation(export_test_env):
    client, _, token2 = export_test_env
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 2 cannot export User 1's resume
    resp_pdf = client.get("/api/v1/resumes/10/export/pdf", headers=headers2)
    assert resp_pdf.status_code == 404

    resp_docx = client.get("/api/v1/resumes/10/export/docx", headers=headers2)
    assert resp_docx.status_code == 404
