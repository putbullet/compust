import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.main import app
from src.app.database import get_db
from src.app.models import Base, Company, Country, CustomizedResume, Job, Resume, User
from src.app.security import create_access_token, hash_password


@pytest.fixture
def auth_download_client(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Create dummy files for PDF and DOCX
    pdf_file = tmp_path / "test_resume_1.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

    docx_file = tmp_path / "test_resume_1.docx"
    docx_file.write_bytes(b"PK\x03\x04\x14\x00\x00\x00\x08\x00test-docx-content")

    monkeypatch.setattr(
        "src.app.services.resume_recreator.get_customized_resume_file_path",
        lambda fname: tmp_path / fname,
    )

    with session_factory() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        u1 = User(email="alice@example.com", password_hash=hash_password("pw1"), is_active=True, created_at=now, updated_at=now)
        u2 = User(email="bob@example.com", password_hash=hash_password("pw2"), is_active=True, created_at=now, updated_at=now)
        db.add_all([u1, u2])
        db.flush()

        # Create Country and Company and Job
        c = Country(name="Morocco", code="MA")
        comp = Company(name="TestCorp", website_url="https://test.ma", active=True, countries=[c])
        db.add(comp)
        db.flush()

        job = Job(
            company_id=comp.id,
            country_id=c.id,
            title="Software Engineer",
            job_url="https://test.ma/job/1",
            discovered_at=now,
            created_at=now,
            updated_at=now,
            active=True,
        )
        db.add(job)
        db.flush()

        base_res = Resume(
            user_id=u1.id,
            filename="base_resume.pdf",
            raw_text="Alice's base resume text",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(base_res)
        db.flush()

        # Create CustomizedResume owned by Alice
        cr1 = CustomizedResume(
            user_id=u1.id,
            base_resume_id=base_res.id,
            job_id=job.id,
            version=1,
            pdf_filename="test_resume_1.pdf",
            docx_filename="test_resume_1.docx",
            raw_text="Alice's customized resume text",
            created_at=now,
        )
        db.add(cr1)
        db.commit()

        u1_token = create_access_token({"sub": str(u1.id)})
        u2_token = create_access_token({"sub": str(u2.id)})
        cr1_id = cr1.id

    client = TestClient(app)
    client.u1_token = u1_token
    client.u2_token = u2_token
    client.cr1_id = cr1_id

    yield client

    app.dependency_overrides.clear()
    engine.dispose()


def test_authenticated_pdf_download_bearer(auth_download_client):
    """Authenticated user downloads PDF using Bearer header."""
    headers = {"Authorization": f"Bearer {auth_download_client.u1_token}"}
    response = auth_download_client.get(
        f"/api/v1/customized-resumes/{auth_download_client.cr1_id}/download/pdf",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "test_resume_1.pdf" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF-")


def test_authenticated_pdf_download_query_token(auth_download_client):
    """Authenticated user downloads PDF using ?token= query parameter."""
    response = auth_download_client.get(
        f"/api/v1/customized-resumes/{auth_download_client.cr1_id}/download/pdf?token={auth_download_client.u1_token}"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_authenticated_docx_download_bearer(auth_download_client):
    """Authenticated user downloads DOCX using Bearer header."""
    headers = {"Authorization": f"Bearer {auth_download_client.u1_token}"}
    response = auth_download_client.get(
        f"/api/v1/customized-resumes/{auth_download_client.cr1_id}/download/docx",
        headers=headers,
    )
    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "test_resume_1.docx" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"PK\x03\x04")


def test_unauthenticated_download_rejected(auth_download_client):
    """Unauthenticated download request returns 401."""
    response = auth_download_client.get(
        f"/api/v1/customized-resumes/{auth_download_client.cr1_id}/download/pdf"
    )
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json().get("detail", "")


def test_invalid_token_download_rejected(auth_download_client):
    """Invalid token returns 401."""
    response = auth_download_client.get(
        f"/api/v1/customized-resumes/{auth_download_client.cr1_id}/download/pdf?token=invalid.garbage.token"
    )
    assert response.status_code == 401


def test_cross_user_download_forbidden(auth_download_client):
    """User B cannot download User A's customized resume."""
    headers = {"Authorization": f"Bearer {auth_download_client.u2_token}"}
    response = auth_download_client.get(
        f"/api/v1/customized-resumes/{auth_download_client.cr1_id}/download/pdf",
        headers=headers,
    )
    assert response.status_code == 404
    assert "Customized resume not found" in response.json().get("detail", "")


def test_nonexistent_resume_id(auth_download_client):
    """Non-existent resume ID returns 404."""
    headers = {"Authorization": f"Bearer {auth_download_client.u1_token}"}
    response = auth_download_client.get(
        "/api/v1/customized-resumes/99999/download/pdf",
        headers=headers,
    )
    assert response.status_code == 404


def test_invalid_format_rejected(auth_download_client):
    """Invalid format parameter (e.g. exe, txt) returns 422 validation error."""
    headers = {"Authorization": f"Bearer {auth_download_client.u1_token}"}
    response = auth_download_client.get(
        f"/api/v1/customized-resumes/{auth_download_client.cr1_id}/download/exe",
        headers=headers,
    )
    assert response.status_code == 422
