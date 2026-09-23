from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app.main import app, extension_rate_limiter
from src.app.models import User, Resume, Job, Company
from src.app.security import create_access_token, hash_password
from src.app.config import get_settings


@pytest.fixture
def auth_user(db_session: Session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = User(
        email="candidate@compust.ma",
        password_hash=hash_password("Password123!"),
        first_name="Jane",
        last_name="Doe",
        is_active=True,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(auth_user: User):
    token = create_access_token({"sub": str(auth_user.id), "email": auth_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def active_resume(db_session: Session, auth_user: User):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    resume = Resume(
        user_id=auth_user.id,
        title="Jane Doe CV",
        filename="jane_doe_cv.pdf",
        raw_text="Jane Doe. Python, FastAPI, Docker, TypeScript, React Developer. Experience 2021-2026.",
        parsed_sections={
            "experience": "Senior Developer at TechCorp (2022 - 2025): Built REST APIs using Python, FastAPI, Docker.",
            "education": "BS Computer Science, 2021",
            "skills": ["Python", "FastAPI", "Docker", "React", "TypeScript", "SQL"],
        },
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


def test_quick_add_success(client: TestClient, auth_headers: dict):
    payload = {
        "title": "Senior Frontend Engineer",
        "company": "LinkedIn Corp",
        "url": "https://www.linkedin.com/jobs/view/123456789/",
        "location": "Casablanca, Morocco",
        "description": "<p>We are seeking a React and TypeScript engineer.</p>",
        "employment_type": "Full-time",
        "remote_type": "Hybrid",
        "source": "extension:linkedin",
    }
    response = client.post("/api/v1/jobs/quick-add", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Senior Frontend Engineer"
    assert data["company"] == "LinkedIn Corp"
    assert data["dedup_status"] == "created"
    assert data["is_duplicate"] is False
    assert data["job_id"] > 0


def test_quick_add_duplicate(client: TestClient, auth_headers: dict):
    payload = {
        "title": "Backend Python Architect",
        "company": "Indeed Inc",
        "url": "https://www.indeed.com/viewjob?jk=abcdef123456",
        "location": "Paris, France",
        "description": "FastAPI and PostgreSQL specialist wanted.",
        "source": "extension:indeed",
    }
    resp1 = client.post("/api/v1/jobs/quick-add", json=payload, headers=auth_headers)
    assert resp1.status_code == 200
    job_id1 = resp1.json()["job_id"]
    assert resp1.json()["is_duplicate"] is False

    # Second submission with same company and URL should deduplicate to the same job row
    resp2 = client.post("/api/v1/jobs/quick-add", json=payload, headers=auth_headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["job_id"] == job_id1
    assert data2["dedup_status"] == "existing"
    assert data2["is_duplicate"] is True


def test_quick_add_and_analyze_with_resume(
    client: TestClient, auth_headers: dict, active_resume: Resume
):
    payload = {
        "title": "Full Stack Engineer",
        "company": "Glassdoor Tech",
        "url": "https://www.glassdoor.com/job-listing/full-stack-112233",
        "location": "Remote",
        "description": "<p>Must have Python, FastAPI, Docker, and React skills.</p>",
        "source": "extension:glassdoor",
    }
    response = client.post(
        "/api/v1/jobs/quick-add-and-analyze", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_active_resume"] is True
    assert data["job"]["title"] == "Full Stack Engineer"
    assert data["match_analysis"] is not None
    assert "already_demonstrated" in data["match_analysis"]
    assert "missing_or_weak" in data["match_analysis"]
    assert data["score_breakdown"] is not None
    assert "overall_score" in data["score_breakdown"]


def test_quick_add_and_analyze_without_resume(client: TestClient, auth_headers: dict):
    payload = {
        "title": "DevOps Engineer",
        "company": "Cloud Corp",
        "url": "https://www.linkedin.com/jobs/view/99887766/",
        "location": "Casablanca, Morocco",
        "description": "Kubernetes and Terraform specialist.",
        "source": "extension:linkedin",
    }
    response = client.post(
        "/api/v1/jobs/quick-add-and-analyze", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_active_resume"] is False
    assert "No active resume set" in data["message"]
    assert data["match_analysis"] is None


def test_input_sanitization_xss(client: TestClient, auth_headers: dict, db_session: Session):
    malicious_desc = '<p>Great job!</p><script>alert("xss")</script><iframe src="evil.com"></iframe><img src=x onerror=alert(1)>'
    payload = {
        "title": "Security Analyst <script>alert(1)</script>",
        "company": "Safe Corp",
        "url": "https://www.indeed.com/viewjob?jk=xss123",
        "location": "Remote",
        "description": malicious_desc,
        "source": "extension:indeed",
    }
    response = client.post("/api/v1/jobs/quick-add", json=payload, headers=auth_headers)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    saved_job = db_session.get(Job, job_id)
    assert saved_job is not None
    assert "<script>" not in saved_job.description
    assert "<iframe" not in saved_job.description
    assert "onerror" not in saved_job.description
    assert "alert" not in saved_job.title


def test_missing_fields_validation(client: TestClient, auth_headers: dict):
    # Missing required title and company
    response = client.post(
        "/api/v1/jobs/quick-add",
        json={"url": "https://linkedin.com/jobs/view/1"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_unauthenticated_rejection(client: TestClient):
    response = client.post(
        "/api/v1/jobs/quick-add",
        json={
            "title": "Engineer",
            "company": "Acme",
            "url": "https://indeed.com/viewjob?jk=1",
        },
    )
    assert response.status_code == 401


def test_rate_limiting(client: TestClient, auth_headers: dict, auth_user: User):
    extension_rate_limiter.reset()
    orig_max = extension_rate_limiter.max_requests
    try:
        extension_rate_limiter.max_requests = 3
        payload = {
            "title": "Rate Limit Test",
            "company": "Burst Corp",
            "url": "https://linkedin.com/jobs/view/ratelimit",
            "source": "extension:test",
        }
        for i in range(3):
            res = client.post("/api/v1/jobs/quick-add", json=payload, headers=auth_headers)
            assert res.status_code == 200

        # 4th request exceeds max_requests=3
        res_blocked = client.post("/api/v1/jobs/quick-add", json=payload, headers=auth_headers)
        assert res_blocked.status_code == 429
        assert "Rate limit exceeded" in res_blocked.json()["detail"]
    finally:
        extension_rate_limiter.max_requests = orig_max
        extension_rate_limiter.reset()


def test_cors_extension_origins_allowed(client: TestClient):
    settings = get_settings()
    # Add a mock extension origin to settings
    test_ext_origin = "chrome-extension://abcdefghijklmnop"
    if test_ext_origin not in settings.extension_allowed_origins:
        settings.extension_allowed_origins.append(test_ext_origin)

    response = client.options(
        "/api/v1/jobs/quick-add",
        headers={
            "Origin": test_ext_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == test_ext_origin


def test_cors_evil_origin_rejected(client: TestClient):
    evil_origin = "https://evil.example.com"
    response = client.options(
        "/api/v1/jobs/quick-add",
        headers={
            "Origin": evil_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    # Evil origin should not have access-control-allow-origin header matching the evil origin
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != evil_origin


def test_quick_add_does_not_create_application(client: TestClient, auth_headers: dict, db_session: Session):
    """Verify Issue 2 requirement: quick-add / analysis stores the job in directory but DOES NOT track in Kanban."""
    # Test 1: plain quick-add
    payload1 = {
        "title": "Untracked Analyzed Role 1",
        "company": "NoTrack Corp 1",
        "location": "Casablanca",
        "description": "Looking for a Python Developer. No auto tracking should happen.",
        "url": "https://www.linkedin.com/jobs/view/999111222/",
        "source": "extension:linkedin",
    }
    response1 = client.post("/api/v1/jobs/quick-add", json=payload1, headers=auth_headers)
    assert response1.status_code == 200
    data1 = response1.json()
    job_id1 = data1["job_id"]

    # Assert job is stored in jobs table
    job_in_db1 = db_session.query(Job).filter(Job.id == job_id1).first()
    assert job_in_db1 is not None
    assert job_in_db1.title == "Untracked Analyzed Role 1"

    # Test 2: quick-add-and-analyze (called directly by extension)
    payload2 = {
        "title": "Untracked Analyzed Role 2",
        "company": "NoTrack Corp 2",
        "location": "Rabat",
        "description": "Looking for a React Developer. No auto tracking should happen either.",
        "url": "https://www.linkedin.com/jobs/view/999111333/",
        "source": "extension:linkedin",
    }
    response2 = client.post("/api/v1/jobs/quick-add-and-analyze", json=payload2, headers=auth_headers)
    assert response2.status_code == 200
    data2 = response2.json()
    job_id2 = data2["job"]["job_id"]

    job_in_db2 = db_session.query(Job).filter(Job.id == job_id2).first()
    assert job_in_db2 is not None
    assert job_in_db2.title == "Untracked Analyzed Role 2"

    # CRITICAL: Assert NO application was created in the user's Applications Kanban for either job
    apps_response = client.get("/api/v1/applications", headers=auth_headers)
    assert apps_response.status_code == 200
    apps = apps_response.json()
    tracked_job_ids = [a.get("job_id") for a in apps]
    assert job_id1 not in tracked_job_ids, "quick-add must NOT automatically create a tracked application in Kanban"
    assert job_id2 not in tracked_job_ids, "quick-add-and-analyze must NOT automatically create a tracked application in Kanban"


def test_extension_download_chrome_and_firefox(client: TestClient):
    """Verify Issue 3 requirement: download endpoints serve real, valid zip files with proper headers."""
    import zipfile
    import io

    for browser in ["chrome", "firefox"]:
        response = client.get(f"/api/v1/extension/download/{browser}")
        assert response.status_code == 200
        assert "application/zip" in response.headers.get("content-type", "")
        expected_filename = f"compust-capture-{browser}.zip"
        assert f'filename="{expected_filename}"' in response.headers.get("content-disposition", "")
        assert len(response.content) > 1000

        # Verify it is a valid zip containing manifest.json
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        namelist = zf.namelist()
        assert "manifest.json" in namelist
        assert any("content/linkedin.js" in name for name in namelist)


def test_analyze_ephemeral_zero_database_writes(client: TestClient, auth_headers: dict, db_session: Session, active_resume: Resume):
    """CRITICAL TEST: Calling /api/v1/jobs/analyze-ephemeral must NOT write anything to the database."""
    job_count_before = db_session.query(Job).count()
    comp_count_before = db_session.query(Company).count()

    from src.app.models import UserApplication
    app_count_before = db_session.query(UserApplication).count()

    payload = {
        "title": "Senior Cloud Architect",
        "company": "Ghost Corporation",
        "url": "https://ghostcorp.com/careers/cloud-architect-101",
        "location": "Remote",
        "description": "<p>Looking for a Senior Cloud Architect with Python, Docker, FastAPI and Kubernetes experience.</p>",
        "employment_type": "Full-time",
        "remote_type": "Remote",
        "source": "extension:generic",
    }

    response = client.post("/api/v1/jobs/analyze-ephemeral", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["title"] == "Senior Cloud Architect"
    assert data["company"] == "Ghost Corporation"
    assert data["has_active_resume"] is True
    assert data["match_score"] is not None
    assert "resume_suggestions" in data
    assert len(data["resume_suggestions"]) > 0
    assert "content_hash" in data

    # Verify each suggestion has section, item_label, where, suggested_text, reason, grounded
    for sugg in data["resume_suggestions"]:
        assert "section" in sugg
        assert "item_label" in sugg
        assert "where" in sugg
        assert "suggested_text" in sugg
        assert "grounded" in sugg

    # ABSOLUTE ZERO DB WRITES CHECK
    db_session.expire_all()
    job_count_after = db_session.query(Job).count()
    comp_count_after = db_session.query(Company).count()
    app_count_after = db_session.query(UserApplication).count()

    assert job_count_after == job_count_before, "analyze-ephemeral must NEVER write a Job row to the database"
    assert comp_count_after == comp_count_before, "analyze-ephemeral must NEVER write a Company row to the database"
    assert app_count_after == app_count_before, "analyze-ephemeral must NEVER write a UserApplication row to the database"


def test_quick_add_with_application_status_applied(client: TestClient, auth_headers: dict, db_session: Session):
    """Test Add + Mark as Applied persists job and tracks in Kanban as 'applied'."""
    suggestions = [
        {
            "id": "sugg-1",
            "section": "skills",
            "item_label": "Docker",
            "action": "add",
            "where": "Skills",
            "suggested_text": "Docker",
            "reason": "Required skill",
            "grounded": True,
        }
    ]
    payload = {
        "title": "DevOps Engineer",
        "company": "Ops Unlimited",
        "url": "https://opsunlimited.com/jobs/devops-1",
        "location": "Paris, France",
        "description": "DevOps role with Docker and CI/CD.",
        "application_status": "applied",
        "resume_suggestions": suggestions,
    }

    response = client.post("/api/v1/jobs/quick-add", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] > 0
    assert data["application_status"] == "applied"
    assert data["application_id"] is not None

    # Check Job in DB
    job = db_session.query(Job).filter(Job.id == data["job_id"]).first()
    assert job is not None
    assert job.resume_suggestions is not None
    assert len(job.resume_suggestions) == 1

    # Check UserApplication in DB
    from src.app.models import UserApplication
    app_row = db_session.query(UserApplication).filter(UserApplication.id == data["application_id"]).first()
    assert app_row is not None
    assert app_row.status == "applied"
    assert app_row.resume_suggestions is not None


def test_quick_add_with_application_status_saved(client: TestClient, auth_headers: dict, db_session: Session):
    """Test Save (Interested) tracks in Kanban as 'saved'."""
    payload = {
        "title": "Machine Learning Engineer",
        "company": "AI Labs",
        "url": "https://ailabs.com/jobs/mle-42",
        "location": "Rabat, Morocco",
        "description": "PyTorch and NLP engineer.",
        "application_status": "saved",
    }

    response = client.post("/api/v1/jobs/quick-add", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["application_status"] == "saved"
    assert data["application_id"] is not None


def test_extract_from_html_endpoint(client: TestClient, auth_headers: dict):
    """Test generic HTML extraction via platform adapters, JSON-LD and title matcher."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lead Full Stack Developer at TechVentures</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Lead Full Stack Developer",
            "hiringOrganization": {
                "@type": "Organization",
                "name": "TechVentures Corp"
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "addressLocality": "Casablanca",
                    "addressCountry": "Morocco"
                }
            },
            "description": "<p>We are seeking a Lead Full Stack Developer skilled in React and Node.js.</p>",
            "employmentType": "FULL_TIME"
        }
        </script>
    </head>
    <body>
        <h1>Lead Full Stack Developer</h1>
    </body>
    </html>
    """
    payload = {
        "html": sample_html,
        "url": "https://careers.techventures.com/jobs/lead-full-stack",
    }
    response = client.post("/api/v1/jobs/extract-from-html", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Lead Full Stack Developer"
    assert data["company"] == "TechVentures Corp"
    assert "Casablanca" in (data["location"] or "")
    assert data["confidence"] in ("high", "medium")
    assert data["normalized_title"] is not None


def test_refresh_job_resume_suggestions(client: TestClient, auth_headers: dict, db_session: Session, active_resume: Resume):
    """Test PUT /api/v1/jobs/{id}/resume-suggestions can re-evaluate suggestions without revisiting posting."""
    # First quick-add a job
    add_payload = {
        "title": "Python Specialist",
        "company": "FastTech",
        "url": "https://fasttech.com/jobs/python-1",
        "description": "Python, Docker and Kubernetes required.",
    }
    add_resp = client.post("/api/v1/jobs/quick-add", json=add_payload, headers=auth_headers)
    job_id = add_resp.json()["job_id"]

    # Refresh suggestions
    put_resp = client.put(f"/api/v1/jobs/{job_id}/resume-suggestions?refresh=true", headers=auth_headers)
    assert put_resp.status_code == 200
    detail = put_resp.json()
    assert detail["resume_suggestions"] is not None
    assert len(detail["resume_suggestions"]) > 0

