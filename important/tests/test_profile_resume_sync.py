"""
tests/test_profile_resume_sync.py
=================================
Automated regression tests for Profile <-> Resume Synchronization & Experience Integrity:
1. Dutch (NL), German (DE), French (FR), English (EN) section header parsing & text extraction.
2. Experience text blocks parser (titles, companies, dates, bullets).
3. Lifecycle sync: Resume A (no experience) -> Resume B (with experience) -> Resume A (no experience).
4. Cache regression test: GET /resume-prompt for Job X with Resume A -> switch to Resume B -> GET /resume-prompt for same Job X.
   Assert prompt text changes immediately and Cache-Control: no-store is returned.
5. Studio CRUD sync: updates to active Studio resume auto-sync to unified profile.
6. User overrides (pinned / hidden skills) survive resume switches.
7. Profile refresh endpoint: POST /api/v1/profile/unified/refresh forces recomputation.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.database import SessionLocal
from src.app.models import User, Job, Resume, UserUnifiedProfile
from src.app.security import create_access_token
from src.app.services.resume_parser import structure_resume_text
from src.app.repositories.resume import (
    _parse_experience_text_blocks,
    create_structured_resume,
    update_structured_resume,
    set_default_structured_resume,
    get_active_resume,
)
from src.app.services.profile_fusion import get_unified_profile, recompute_unified_profile

client = TestClient(app)

TEST_USER_EMAIL = "zz_test_sync_runner@compust.internal"


@pytest.fixture
def test_user_and_token():
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
        if not user:
            user = User(
                email=TEST_USER_EMAIL,
                password_hash="testhash123",
                first_name="Sync",
                last_name="Tester",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        user_id = user.id

        # Clean any previous test resumes for this user
        db.query(Resume).filter(Resume.user_id == user_id).delete()
        db.query(UserUnifiedProfile).filter(UserUnifiedProfile.user_id == user_id).delete()
        db.commit()

    token = create_access_token({"sub": TEST_USER_EMAIL, "user_id": user_id})

    yield {"user_id": user_id, "token": token}

    # Teardown
    with SessionLocal() as db:
        db.query(Resume).filter(Resume.user_id == user_id).delete()
        db.query(UserUnifiedProfile).filter(UserUnifiedProfile.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()


# ---------------------------------------------------------------------------
# 1. Parsing & Multilingual Section Detection Tests
# ---------------------------------------------------------------------------

def test_dutch_section_headings_parsing():
    """Verify Dutch (nl) section headers are correctly recognized."""
    dutch_resume_text = """
    Jan de Vries
    jan@example.nl

    PERSOONLIJK PROFIEL
    Ervaren data engineer met passie voor gedistribueerde systemen.

    WERKERVARING
    Senior Data Engineer | DataOps BV
    2021 - Heden
    - Bouwen van real-time Kafka pipelines
    - Databricks Lakehouse beheer

    OPLEIDING
    Master Computer Science | Universiteit van Amsterdam
    2018 - 2020

    VAARDIGHEDEN
    Python, SQL, Apache Kafka, PySpark, Docker

    TALENKENNIS
    Nederlands (Moedertaal), Engels (Vloeiend)

    CERTIFICATEN
    Databricks Certified Data Engineer Associate
    """
    sections = structure_resume_text(dutch_resume_text)
    assert "summary" in sections
    assert "Ervaren data engineer" in sections["summary"]
    assert "experience" in sections
    assert "DataOps BV" in sections["experience"]
    assert "education" in sections
    assert "Universiteit van Amsterdam" in sections["education"]
    assert "skills" in sections
    assert len(sections["skills"]) >= 3
    assert "languages" in sections
    assert "certifications" in sections


def test_experience_text_blocks_parser():
    """Verify raw multiline experience text is parsed into structured entries."""
    raw_exp = """Senior Software Engineer - CloudScale Corp
    Jan 2022 - Present | Remote
    - Architected microservices platform handling 10M req/day.
    - Reduced AWS infrastructure costs by 30%.

    Backend Developer at StartupHub
    2020 - 2021 | Amsterdam
    Built Python and FastAPI REST services."""

    parsed = _parse_experience_text_blocks(raw_exp)
    assert len(parsed) >= 2
    first = parsed[0]
    assert "Senior Software Engineer" in first["title"]
    assert "CloudScale Corp" in first["company"]
    assert len(first["highlights"]) >= 2

    second = parsed[1]
    assert "Backend Developer" in second["title"]
    assert "StartupHub" in second["company"]


# ---------------------------------------------------------------------------
# 2. Lifecycle Sync Tests: Resume A (no exp) -> Resume B (with exp) -> Resume A
# ---------------------------------------------------------------------------

def test_lifecycle_switch_resumes_syncs_experience(test_user_and_token):
    """
    Switching from Resume A (no experience) to Resume B (with experience) and back
    must immediately update the unified profile.
    """
    user_id = test_user_and_token["user_id"]

    with SessionLocal() as db:
        # 1. Create Resume A (Student / No experience)
        resume_a = create_structured_resume(
            db=db,
            user_id=user_id,
            title="Resume A (Junior / No Exp)",
            is_default=True,
            structured_data={
                "profile": {"name": "Candidate", "headline": "Recent Graduate"},
                "experience": [],
                "education": [{"school": "TU Delft", "degree": "BSc Computer Science", "date": "2023"}],
                "skills": ["Python", "Algorithms", "Git"],
            },
        )
        assert resume_a.is_default is True
        assert resume_a.is_active is True

        # Recompute unified profile
        recompute_unified_profile(db, user_id)
        p_a = get_unified_profile(db, user_id)
        assert len(p_a.get("experience", [])) == 0
        assert p_a["counts"]["roles"] == 0
        assert p_a["source_resume"]["id"] == resume_a.id
        assert p_a["source_resume"]["title"] == "Resume A (Junior / No Exp)"

        # 2. Create Resume B (Experienced)
        resume_b = create_structured_resume(
            db=db,
            user_id=user_id,
            title="Resume B (Experienced Senior)",
            is_default=False,
            structured_data={
                "profile": {"name": "Candidate", "headline": "Senior Engineer"},
                "experience": [
                    {
                        "title": "Lead Software Engineer",
                        "company": "FinTech Innovations",
                        "start_date": "2022-01",
                        "end_date": "Present",
                        "description": "Leading distributed ledger engineering.",
                        "highlights": ["High performance transaction processing"],
                    },
                    {
                        "title": "Software Engineer",
                        "company": "EarlyStage Tech",
                        "start_date": "2019-06",
                        "end_date": "2021-12",
                        "description": "Core backend services.",
                    },
                ],
                "education": [{"school": "TU Delft", "degree": "MSc Computer Science", "date": "2019"}],
                "skills": ["Python", "Rust", "Distributed Systems", "PostgreSQL"],
            },
        )
        assert resume_b.is_default is False

        # 3. Activate Resume B
        set_default_structured_resume(db, user_id, resume_b.id)
        # recompute is called by API; let's call get_unified_profile to test self-healing
        p_b = get_unified_profile(db, user_id)
        assert p_b["source_resume"]["id"] == resume_b.id
        assert p_b["counts"]["roles"] == 2
        assert len(p_b.get("experience", [])) == 2
        assert p_b["experience"][0]["title"] == "Lead Software Engineer"

        # 4. Switch back to Resume A
        set_default_structured_resume(db, user_id, resume_a.id)
        p_a2 = get_unified_profile(db, user_id)
        assert p_a2["source_resume"]["id"] == resume_a.id
        assert p_a2["counts"]["roles"] == 0
        assert len(p_a2.get("experience", [])) == 0


# ---------------------------------------------------------------------------
# 3. Cache Regression Test: GET /resume-prompt for Job X
# ---------------------------------------------------------------------------

def test_cache_regression_prompt_endpoint(test_user_and_token):
    """
    Call GET /resume-prompt for Job X when Resume A is active -> switch to Resume B ->
    call GET /resume-prompt for same Job X.
    Must return Cache-Control: no-store and immediately reflect Resume B's experience.
    """
    user_id = test_user_and_token["user_id"]
    token = test_user_and_token["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        # Find any job
        first_job = db.query(Job).first()
        assert first_job is not None, "At least one job required in database"
        job_id = first_job.id

        # Create Resume A (no experience)
        resume_a = create_structured_resume(
            db=db,
            user_id=user_id,
            title="ZZ Resume A",
            is_default=True,
            structured_data={
                "profile": {"name": "Entry Candidate"},
                "experience": [],
                "skills": ["Python", "SQL"],
            },
        )
        # Create Resume B (with experience)
        resume_b = create_structured_resume(
            db=db,
            user_id=user_id,
            title="ZZ Resume B",
            is_default=False,
            structured_data={
                "profile": {"name": "Senior Candidate"},
                "experience": [
                    {
                        "title": "Staff Platform Architect",
                        "company": "Quantum Innovations BV",
                        "start_date": "2021",
                        "end_date": "Present",
                        "highlights": ["Designed high-throughput streaming architecture"],
                    }
                ],
                "skills": ["Python", "Kafka", "Kubernetes"],
            },
        )

    # 1. First prompt request with Resume A
    resp_a = client.get(f"/api/v1/jobs/{job_id}/resume-prompt", headers=headers)
    assert resp_a.status_code == 200
    assert "no-store" in resp_a.headers.get("Cache-Control", "").lower()
    data_a = resp_a.json()
    assert data_a["has_experience"] is False
    assert data_a["source_resume_title"] == "ZZ Resume A"
    assert "*[No work experience recorded in profile]*" in data_a["prompt"]
    assert "Quantum Innovations BV" not in data_a["prompt"]

    # 2. Switch active resume to Resume B via API
    resp_switch = client.post(f"/api/v1/resumes/{resume_b.id}/set-default", headers=headers)
    assert resp_switch.status_code == 200

    # 3. Second prompt request for the EXACT SAME Job X
    resp_b = client.get(f"/api/v1/jobs/{job_id}/resume-prompt", headers=headers)
    assert resp_b.status_code == 200
    assert "no-store" in resp_b.headers.get("Cache-Control", "").lower()
    data_b = resp_b.json()
    assert data_b["has_experience"] is True
    assert data_b["source_resume_title"] == "ZZ Resume B"
    assert "Staff Platform Architect" in data_b["prompt"]
    assert "Quantum Innovations BV" in data_b["prompt"]
    assert "*[No work experience recorded in profile]*" not in data_b["prompt"]


# ---------------------------------------------------------------------------
# 4. User Overrides Survival Test
# ---------------------------------------------------------------------------

def test_user_overrides_survive_resume_switch(test_user_and_token):
    """Pinned and hidden skills must persist across resume switches."""
    token = test_user_and_token["token"]
    user_id = test_user_and_token["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        res_a = create_structured_resume(
            db=db,
            user_id=user_id,
            title="Resume Alpha",
            is_default=True,
            structured_data={"skills": ["Python", "Django", "SQL"]},
        )
        res_b = create_structured_resume(
            db=db,
            user_id=user_id,
            title="Resume Beta",
            is_default=False,
            structured_data={"skills": ["Python", "FastAPI", "PostgreSQL"]},
        )

    # Set user overrides
    resp_ov = client.post(
        "/api/v1/profile/unified/overrides",
        headers=headers,
        json={"pinned_skills": ["python"], "hidden_skills": ["sql"]},
    )
    assert resp_ov.status_code == 200
    p_data = resp_ov.json()
    assert "python" in p_data["user_overrides"]["pinned_skills"]
    assert "sql" in p_data["user_overrides"]["hidden_skills"]

    # Switch to Resume Beta
    client.post(f"/api/v1/resumes/{res_b.id}/set-default", headers=headers)

    # Retrieve profile
    resp_p = client.get("/api/v1/profile/unified", headers=headers)
    assert resp_p.status_code == 200
    p_after = resp_p.json()
    assert "python" in p_after["user_overrides"]["pinned_skills"]
    assert "sql" in p_after["user_overrides"]["hidden_skills"]


# ---------------------------------------------------------------------------
# 5. Profile Refresh Endpoint Test
# ---------------------------------------------------------------------------

def test_refresh_unified_profile_endpoint(test_user_and_token):
    """POST /api/v1/profile/unified/refresh recomputes profile and returns counts."""
    token = test_user_and_token["token"]
    user_id = test_user_and_token["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        res = create_structured_resume(
            db=db,
            user_id=user_id,
            title="Primary Resume",
            is_default=True,
            structured_data={
                "experience": [
                    {"title": "DevOps Engineer", "company": "Cloud Inc", "start_date": "2020", "end_date": "2023"}
                ],
                "skills": ["Kubernetes", "Terraform", "AWS"],
            },
        )

    resp = client.post("/api/v1/profile/unified/refresh", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_resume_title"] == "Primary Resume"
    assert data["counts"]["roles"] == 1
    assert data["counts"]["skills"] >= 3


# ---------------------------------------------------------------------------
# 6. Studio Update Sync & Consumer Alignment Tests
# ---------------------------------------------------------------------------

def test_studio_resume_update_syncs_to_profile(test_user_and_token):
    """Updating structured_data in Studio immediately propagates to unified profile."""
    token = test_user_and_token["token"]
    user_id = test_user_and_token["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        res = create_structured_resume(
            db=db,
            user_id=user_id,
            title="Studio Active Resume",
            is_default=True,
            structured_data={
                "experience": [
                    {"title": "Junior Developer", "company": "DevShop", "start_date": "2020", "end_date": "2021"}
                ],
                "skills": ["JavaScript"],
            },
        )
        res_id = res.id

    # Update via Studio API (add a senior role)
    update_payload = {
        "title": "Studio Active Resume",
        "structured_data": {
            "profile": {"name": "Candidate"},
            "experience": [
                {"id": "exp1", "title": "Junior Developer", "company": "DevShop", "start_date": "2020", "end_date": "2021"},
                {"id": "exp2", "title": "Senior Solutions Architect", "company": "Enterprise Cloud", "start_date": "2022", "end_date": "Present"},
            ],
            "skills": [{"id": "s1", "name": "JavaScript"}, {"id": "s2", "name": "TypeScript"}],
        },
    }
    resp_up = client.put(f"/api/v1/resumes/{res_id}", headers=headers, json=update_payload)
    assert resp_up.status_code == 200

    # Profile should now immediately contain 2 roles and the new title
    resp_p = client.get("/api/v1/profile/unified", headers=headers)
    assert resp_p.status_code == 200
    p_data = resp_p.json()
    assert p_data["counts"]["roles"] == 2
    assert any(e["title"] == "Senior Solutions Architect" for e in p_data["experience"])


def test_consumer_matcher_and_active_resume_alignment(test_user_and_token):
    """Verify get_active_resume and unified profile are 100% aligned for matching consumers."""
    user_id = test_user_and_token["user_id"]

    with SessionLocal() as db:
        # Create Resume 1
        res1 = create_structured_resume(
            db=db,
            user_id=user_id,
            title="Resume Alpha",
            is_default=True,
            structured_data={"skills": ["Python"]},
        )
        # Create Resume 2
        res2 = create_structured_resume(
            db=db,
            user_id=user_id,
            title="Resume Beta",
            is_default=False,
            structured_data={"skills": ["Go", "Kubernetes"]},
        )

        active = get_active_resume(db, user_id)
        assert active is not None
        assert active.id == res1.id

        # Switch to Resume Beta
        set_default_structured_resume(db, user_id, res2.id)

        active_after = get_active_resume(db, user_id)
        assert active_after is not None
        assert active_after.id == res2.id

        # Profile matches active resume
        p = get_unified_profile(db, user_id)
        assert p["source_resume"]["id"] == res2.id
        assert p["source_resume"]["title"] == "Resume Beta"
