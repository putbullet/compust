import io
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy.orm import Session

from src.app.models import Job, User
from src.app.services.resume_parser import (
    ScannedPdfError,
    extract_text_from_pdf_bytes,
    structure_resume_text,
)


def create_blank_scanned_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_sample_text_pdf_bytes() -> bytes:
    return b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 280 >> stream
BT /F1 12 Tf 72 712 Td (Summary) Tj ET
BT /F1 12 Tf 72 690 Td (Software Engineer with 4 years in Python backend development) Tj ET
BT /F1 12 Tf 72 660 Td (Skills) Tj ET
BT /F1 12 Tf 72 640 Td (Python, FastAPI, Docker, SQL, Git, Linux) Tj ET
BT /F1 12 Tf 72 610 Td (Experience) Tj ET
BT /F1 12 Tf 72 590 Td (Backend Developer at TechCorp building APIs) Tj ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000227 00000 n 
0000000558 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
633
%%EOF"""


def test_pdf_extraction_and_scanned_rejection() -> None:
    # 1. Test text-based PDF
    valid_bytes = create_sample_text_pdf_bytes()
    text = extract_text_from_pdf_bytes(valid_bytes)
    assert "Software Engineer" in text
    assert "Python" in text

    # 2. Test scanned / blank PDF -> MUST raise ScannedPdfError
    blank_bytes = create_blank_scanned_pdf_bytes()
    with pytest.raises(ScannedPdfError) as exc_info:
        extract_text_from_pdf_bytes(blank_bytes)
    assert "This PDF does not contain extractable text. Please upload a text-based PDF." in str(exc_info.value)


def test_resume_structuring_heuristics() -> None:
    raw_resume = """
    Summary
    Full-stack developer with 5 years experience building scalable web applications.

    Skills
    Python, TypeScript, React, Docker, PostgreSQL, Redis

    Work Experience
    Senior Software Engineer at Alpha Tech (2022-2026)
    Developed high-throughput financial microservices using FastAPI.

    Education
    Master of Computer Science from University of Casablanca

    Languages
    French, English, Arabic
    """
    structured = structure_resume_text(raw_resume)
    assert "scalable web applications" in structured["summary"]
    assert "Python" in structured["skills"]
    assert "Docker" in structured["skills"]
    assert "Alpha Tech" in structured["experience"]
    assert "Master of Computer Science" in structured["education"]
    assert len(structured["languages"]) >= 1


def test_resume_upload_and_customization_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    # Register/login user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": "resumetest@compust.ma", "password": "SecurePassword123!"},
    )
    token = reg_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Try uploading non-PDF
    bad_upload = client.post(
        "/api/v1/profile/resume",
        headers=auth_headers,
        files={"file": ("resume.docx", b"dummy content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert bad_upload.status_code == 400
    assert "Only PDF documents are supported" in bad_upload.json()["detail"]

    # 2. Try uploading scanned/empty PDF
    blank_pdf = create_blank_scanned_pdf_bytes()
    scanned_upload = client.post(
        "/api/v1/profile/resume",
        headers=auth_headers,
        files={"file": ("scanned_resume.pdf", blank_pdf, "application/pdf")},
    )
    assert scanned_upload.status_code == 400
    assert "This PDF does not contain extractable text. Please upload a text-based PDF." in scanned_upload.json()["detail"]

    # 3. Upload valid text PDF
    valid_pdf = create_sample_text_pdf_bytes()
    success_upload = client.post(
        "/api/v1/profile/resume",
        headers=auth_headers,
        files={"file": ("candidate_resume.pdf", valid_pdf, "application/pdf")},
    )
    assert success_upload.status_code == 201
    resume_data = success_upload.json()
    assert resume_data["filename"] == "candidate_resume.pdf"
    assert resume_data["is_active"] is True
    resume_id = resume_data["id"]

    # 4. Get active resume
    get_res = client.get("/api/v1/profile/resume", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == resume_id

    # 5. Get resume suggestions for a job
    job = db_session.query(Job).first()
    assert job is not None

    sug_res = client.post(
        f"/api/v1/jobs/{job.id}/resume-suggestions",
        headers=auth_headers,
    )
    assert sug_res.status_code == 200
    suggestions_data = sug_res.json()
    assert "already_demonstrated" in suggestions_data
    assert "missing_or_weak" in suggestions_data
    assert "suggestions" in suggestions_data
    assert len(suggestions_data["suggestions"]) > 0

    # 6. Delete resume
    del_res = client.delete(f"/api/v1/profile/resume/{resume_id}", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
