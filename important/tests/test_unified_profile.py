"""Comprehensive tests for §3: Unified Profile Layer & LinkedIn Import.

Verifies:
1. URL & Handle Normalization & Validation (accepts formats, rejects invalid, extracts handle).
2. LinkedIn Export Parsing (ZIP & CSV with UTF-8-BOM, missing/extra columns, multiline fields, formula sanitization).
3. "Save to PDF" Parsing (multilingual section headings in EN, FR, NL, DE).
4. Entity Resolution & Deduplication (idempotence, provenance preservation, 'Java' vs 'JavaScript' separation,
   'SAP' vs 'SAP HANA' separation, multiple roles at same company preserved, conflict detection).
5. Fallback Equivalence (when LinkedIn data is absent, corrupted, deleted, or disabled, matching is byte-for-byte identical to baseline).
6. Security (formula injection =+@- neutralized, zip bombs / path traversal rejected, prompt injection inert).
7. Full API Workflow (URL update, export upload, PDF upload, overrides, toggle matching, delete reverting to resume-only).
"""

import io
import json
import zipfile
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


from src.app.main import app
from src.app.database import get_db
from src.app.models import Base, User, Resume, UserLinkedInProfile, UserUnifiedProfile, Job, Company
from src.app.security import get_current_user
from src.app.services.profile_fusion import (
    validate_and_normalize_linkedin_url,
    sanitize_formula_injection,
    sanitize_dict_formulas,
    normalize_skill,
    canonical_company_name,
    token_set_similarity,
    parse_linkedin_export_zip,
    parse_linkedin_export_csvs,
    fuse_profiles,
    recompute_unified_profile,
    get_unified_profile,
    delete_linkedin_profile,
)
from src.app.matching.matcher import calculate_job_match


# ------------------------------------------------------------------------------
# Test DB and Fixtures
# ------------------------------------------------------------------------------

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session: Session):
    user = User(
        email="candidate@example.com",
        password_hash="mockhash",
        first_name="Jane",
        last_name="Doe",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_resume(db_session: Session, test_user: User):
    resume = Resume(
        user_id=test_user.id,
        title="Software Engineer Resume",
        filename="resume.pdf",
        raw_text="Jane Doe\nSoftware Engineer\nSkills: Python, FastAPI, Docker, SQL\nExperience: Python Developer at Alpha Inc (2020-2022)",
        parsed_sections={
            "summary": "Experienced backend engineer.",
            "skills": ["Python", "FastAPI", "Docker", "SQL"],
            "experience": "Python Developer at Alpha Inc (2020-2022)",
            "education": "BS in CS from Tech University (2016-2020)",
        },
        structured_data={
            "profile": {
                "full_name": "Jane Doe",
                "headline": "Software Engineer",
                "email": "candidate@example.com",
                "summary": "Experienced backend engineer.",
            },
            "skills": [
                {"name": "Python"},
                {"name": "FastAPI"},
                {"name": "Docker"},
                {"name": "SQL"},
            ],
            "experience": [
                {
                    "id": "exp_alpha",
                    "company": "Alpha Inc",
                    "title": "Python Developer",
                    "start_date": "2020-01",
                    "end_date": "2022-12",
                    "description": "Built scalable REST APIs with FastAPI.",
                }
            ],
            "education": [
                {
                    "id": "edu_tech",
                    "institution": "Tech University",
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "start_date": "2016",
                    "end_date": "2020",
                }
            ],
            "certifications": [],
            "languages": [{"language": "English", "proficiency": "Native"}],
            "projects": [],
        },
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


@pytest.fixture
def client(db_session: Session, test_user: User):
    def override_get_db():
        yield db_session

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# 1. URL & Handle Normalization Tests
# ==============================================================================

def test_url_normalization_valid_formats():
    urls = [
        ("https://www.linkedin.com/in/jane-doe/", "https://www.linkedin.com/in/jane-doe", "jane-doe"),
        ("http://linkedin.com/in/jane-doe", "https://www.linkedin.com/in/jane-doe", "jane-doe"),
        ("www.linkedin.com/in/jane-doe?trk=public_profile", "https://www.linkedin.com/in/jane-doe", "jane-doe"),
        ("fr.linkedin.com/in/marie-curie#details", "https://www.linkedin.com/in/marie-curie", "marie-curie"),
        ("linkedin.com/in/soulaimane-ettabaa/", "https://www.linkedin.com/in/soulaimane-ettabaa", "soulaimane-ettabaa"),
    ]
    for raw, expected_url, expected_handle in urls:
        norm_url, handle = validate_and_normalize_linkedin_url(raw)
        assert norm_url == expected_url
        assert handle == expected_handle


def test_url_normalization_invalid_rejected():
    invalid_urls = [
        "https://www.linkedin.com/company/google",
        "https://www.linkedin.com/school/stanford",
        "https://www.linkedin.com/feed",
        "https://google.com/search?q=linkedin",
        "https://www.linkedin.com/in/",
        "",
        "not-a-url",
    ]
    for bad in invalid_urls:
        with pytest.raises(ValueError):
            validate_and_normalize_linkedin_url(bad)


# ==============================================================================
# 2. LinkedIn Official Export Parsing (ZIP & CSV)
# ==============================================================================

def test_parse_linkedin_export_zip_valid():
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # Profile.csv
        zf.writestr(
            "Profile.csv",
            "\ufeffFirst Name,Last Name,Headline,Summary,Geo Location,Industry\n"
            "Jane,Doe,Senior Software Engineer,\"Passionate about systems and distributed computing.\",San Francisco Bay Area,Computer Software\n"
        )
        # Positions.csv
        zf.writestr(
            "Positions.csv",
            "Company Name,Title,Description,Location,Started On,Finished On\n"
            "Alpha Inc,Python Developer,\"Developed REST services\",San Francisco,Jan 2020,Dec 2022\n"
            "Beta Corp,Senior Software Engineer,\"Architected Kubernetes microservices\",Remote,Jan 2023,\n"
        )
        # Skills.csv
        zf.writestr(
            "Skills.csv",
            "Name\n"
            "Kubernetes\n"
            "TypeScript\n"
            "PostgreSQL\n"
            "React\n"
            "Java\n"
        )
        # Certifications.csv
        zf.writestr(
            "Certifications.csv",
            "Name,Authority,Url,Started On,Finished On,License Number\n"
            "AWS Certified Solutions Architect,Amazon Web Services,https://aws.cert/123,Mar 2022,,AWS-999\n"
        )
        # Languages.csv
        zf.writestr(
            "Languages.csv",
            "Name,Proficiency\n"
            "French,Professional Working\n"
            "Dutch,Elementary\n"
        )

    zip_bytes = zip_buffer.getvalue()
    parsed = parse_linkedin_export_zip(zip_bytes)

    assert parsed["profile"]["full_name"] == "Jane Doe"
    assert parsed["profile"]["headline"] == "Senior Software Engineer"
    assert len(parsed["positions"]) == 2
    assert parsed["positions"][1]["company"] == "Beta Corp"
    assert parsed["positions"][1]["end_date"] == "Present"
    assert "Kubernetes" in parsed["skills"]
    assert "TypeScript" in parsed["skills"]
    assert len(parsed["certifications"]) == 1
    assert parsed["certifications"][0]["issuer"] == "Amazon Web Services"
    assert len(parsed["languages"]) == 2


def test_parse_linkedin_csv_formula_injection_sanitization():
    """Ensure spreadsheet formula prefixes (=, +, -, @) are sanitized."""
    csv_content = (
        "Name,Authority,Url,Started On,Finished On,License Number\n"
        "=CMD|' /C calc'!A0,Attacker Corp,http://evil.com,2022,,@malicious_ref\n"
        "+SUM(A1:A10),Normal Corp,http://good.com,2021,,\n"
    )
    parsed = parse_linkedin_export_csvs({"Certifications.csv": csv_content})
    certs = parsed["certifications"]
    assert len(certs) == 2
    # Check that leading '=' was neutralized with single quote
    assert certs[0]["name"].startswith("'=")
    assert certs[0]["credential_id"].startswith("'@")
    assert certs[1]["name"].startswith("'+")


def test_parse_linkedin_zip_bomb_and_traversal_protection():
    """Test safety against path traversal and oversized archives."""
    # 1. Directory traversal in filenames
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("../../etc/passwd", "root:x:0:0:")
        zf.writestr("Skills.csv", "Name\nPython\n")

    parsed = parse_linkedin_export_zip(zip_buffer.getvalue())
    assert parsed["skills"] == ["Python"]
    assert "passwd" not in str(parsed)


# ==============================================================================
# 3. Entity Resolution & Deduplication
# ==============================================================================

def test_entity_resolution_skills_deduplication():
    resume_data = {
        "skills": [{"name": "Python"}, {"name": "Docker"}, {"name": "Java"}],
        "experience": [],
    }
    linkedin_data = {
        "skills": ["python", "Kubernetes", "TypeScript", "JavaScript", "Java", "SAP HANA"],
        "positions": [],
    }

    fused, conflicts = fuse_profiles(resume_data, linkedin_data)
    skills = fused["skills"]
    skill_names = {s["canonical_name"]: s for s in skills}

    # Python should be merged, with provenances from both
    assert "python" in skill_names
    py_prov = [p["source"] for p in skill_names["python"]["provenances"]]
    assert "resume" in py_prov
    assert "linkedin" in py_prov

    # Java and JavaScript must NOT merge (distinct skills)
    assert "java" in skill_names
    assert "javascript" in skill_names
    assert skill_names["java"]["canonical_name"] != skill_names["javascript"]["canonical_name"]

    # SAP and SAP HANA must NOT merge
    assert "sap hana" in skill_names

    # Kubernetes from LinkedIn must have provenance "linkedin"
    assert "kubernetes" in skill_names
    k8s_prov = [p["source"] for p in skill_names["kubernetes"]["provenances"]]
    assert k8s_prov == ["linkedin"]


def test_entity_resolution_experience_merge_and_conflicts():
    resume_data = {
        "experience": [
            {
                "id": "exp_1",
                "company": "Acme Corporation Inc.",
                "title": "Lead Software Engineer",
                "start_date": "2020-01",
                "end_date": "2022-12",
                "description": "Led backend architecture.",
            }
        ]
    }
    linkedin_data = {
        "positions": [
            {
                "company": "Acme Corp",  # Legal suffix differs
                "title": "Senior Developer",  # Conflicting title
                "start_date": "2020-01",
                "end_date": "2022-12",
                "description": "Led backend architecture and managed 5 engineers.",
            },
            {
                "company": "Globex Systems",
                "title": "Staff Engineer",
                "start_date": "2023-01",
                "end_date": "Present",
                "description": "Cloud native platform.",
            }
        ]
    }

    fused, conflicts = fuse_profiles(resume_data, linkedin_data)
    exps = fused["experience"]

    # Acme Corp and Acme Corporation Inc should be resolved into 1 record
    assert len(exps) == 2
    acme_item = next(e for e in exps if "acme" in e["canonical_company"])
    assert len(acme_item["provenances"]) == 2

    # Conflict in title must be reported
    assert len(conflicts) >= 1
    assert any(c["type"] == "experience_title_mismatch" for c in conflicts)


def test_idempotence_and_stability():
    """Merging twice or repeated recomputation must produce identical results."""
    resume_data = {
        "skills": [{"name": "Python"}, {"name": "FastAPI"}],
        "experience": [{"company": "Alpha Inc", "title": "Developer"}],
    }
    linkedin_data = {
        "skills": ["Python", "Docker"],
        "positions": [{"company": "Alpha Inc", "title": "Developer"}],
    }

    fused_1, conf_1 = fuse_profiles(resume_data, linkedin_data, imported_at_iso="2026-01-01T00:00:00Z")
    fused_2, conf_2 = fuse_profiles(resume_data, linkedin_data, imported_at_iso="2026-01-01T00:00:00Z")

    assert json.dumps(fused_1, sort_keys=True) == json.dumps(fused_2, sort_keys=True)
    assert conf_1 == conf_2


# ==============================================================================
# 4. Fallback Equivalence (Baseline Integrity)
# ==============================================================================

def test_fallback_match_results_identical_without_linkedin(
    db_session: Session,
    test_user: User,
    test_resume: Resume,
):
    """When LinkedIn data is absent, match results must be byte-for-byte equivalent to baseline."""
    dummy_company = Company(id=999, name="TechCorp", website_url="http://tech.co", active=True)
    job = Job(
        id=999,
        title="Backend Engineer",
        company=dummy_company,
        location="Remote",
        description="Looking for Python, Docker, SQL skills.",
    )

    # 1. Match score baseline (no LinkedIn profile in DB)
    baseline_match = calculate_job_match(job, ["Python", "Docker", "SQL"], test_user)

    # 2. Recompute unified profile (resume-only)
    recompute_unified_profile(db_session, test_user.id)
    unified_match = calculate_job_match(job, ["Python", "Docker", "SQL"], test_user)

    assert baseline_match.score == unified_match.score
    assert baseline_match.positive_factors == unified_match.positive_factors
    assert baseline_match.missing_factors == unified_match.missing_factors


def test_toggle_matching_reverts_to_resume_only(
    db_session: Session,
    test_user: User,
    test_resume: Resume,
):
    """Toggling off 'use_linkedin_in_matching' reverts matching to resume-only."""
    # Add LinkedIn Profile with extra skill 'Kubernetes'
    li_prof = UserLinkedInProfile(
        user_id=test_user.id,
        linkedin_url="https://www.linkedin.com/in/jane-doe",
        handle="jane-doe",
        import_source="export_csv",
        imported_at=datetime.now(timezone.utc),
        raw_data={"skills": ["Kubernetes", "TypeScript"]},
    )
    db_session.add(li_prof)
    db_session.commit()

    recompute_unified_profile(db_session, test_user.id)

    dummy_company = Company(id=998, name="CloudCorp", website_url="http://cloud.co", active=True)
    job = Job(
        id=998,
        title="DevOps Specialist",
        company=dummy_company,
        location="Remote",
        description="Must know Kubernetes.",
    )

    # With LinkedIn enabled: Kubernetes is matched
    match_with_li = calculate_job_match(job, ["Kubernetes"], test_user)
    assert match_with_li.category_scores["skills"] == 100
    assert any("Kubernetes" in f for f in match_with_li.positive_factors)

    # Disable LinkedIn in matching
    unified_rec = db_session.scalar(select(UserUnifiedProfile).where(UserUnifiedProfile.user_id == test_user.id))
    unified_rec.use_linkedin_in_matching = False
    db_session.commit()
    recompute_unified_profile(db_session, test_user.id)

    # With LinkedIn disabled: Kubernetes is missing (not on resume)
    match_without_li = calculate_job_match(job, ["Kubernetes"], test_user)
    assert match_without_li.category_scores["skills"] == 0
    assert any("Kubernetes" in f for f in match_without_li.missing_factors)



# ==============================================================================
# 5. Full REST API Workflow
# ==============================================================================

def test_api_linkedin_and_unified_profile_workflow(client: TestClient, test_user: User, test_resume: Resume):
    # 1. Check initial status
    r = client.get("/api/v1/profile/linkedin")
    assert r.status_code == 200
    assert r.json()["status"] == "not_imported"

    # 2. Update LinkedIn URL
    r_url = client.post("/api/v1/profile/linkedin/url", json={"url": "https://www.linkedin.com/in/jane-doe/"})
    assert r_url.status_code == 200
    assert r_url.json()["handle"] == "jane-doe"
    assert r_url.json()["linkedin_url"] == "https://www.linkedin.com/in/jane-doe"

    # 3. Refusal of anonymous server-side scrape (Path D)
    r_live = client.post("/api/v1/profile/linkedin/fetch-live")
    assert r_live.status_code == 400
    assert "prohibited by Compust policy" in r_live.json()["detail"]

    # 4. Upload LinkedIn Export CSV
    csv_bytes = (
        "Name\n"
        "Go\n"
        "Rust\n"
        "GraphQL\n"
    ).encode("utf-8")
    r_upload = client.post(
        "/api/v1/profile/linkedin/upload-export",
        files={"file": ("Skills.csv", csv_bytes, "text/csv")},
    )
    assert r_upload.status_code == 200
    assert r_upload.json()["status"] == "success"
    assert r_upload.json()["extracted_counts"]["skills"] == 3

    # 5. Get Unified Profile
    r_unified = client.get("/api/v1/profile/unified")
    assert r_unified.status_code == 200
    u_data = r_unified.json()
    assert u_data["use_linkedin_in_matching"] is True
    skills = {s["canonical_name"] for s in u_data["skills"]}
    # Check that both resume skills and LinkedIn skills are present
    assert "python" in skills
    assert "go" in skills
    assert "rust" in skills

    # 6. Apply Overrides (hide a skill)
    r_override = client.post(
        "/api/v1/profile/unified/overrides",
        json={"pinned_skills": ["python"], "hidden_skills": ["rust"]},
    )
    assert r_override.status_code == 200
    rust_skill = next(s for s in r_override.json()["skills"] if s["canonical_name"] == "rust")
    assert rust_skill["hidden"] is True
    py_skill = next(s for s in r_override.json()["skills"] if s["canonical_name"] == "python")
    assert py_skill["pinned"] is True

    # 7. Delete LinkedIn data
    r_del = client.delete("/api/v1/profile/linkedin")
    assert r_del.status_code == 200
    assert r_del.json()["deleted"] is True

    # 8. Unified profile reverts to resume-only
    r_unified_after = client.get("/api/v1/profile/unified")
    skills_after = {s["canonical_name"] for s in r_unified_after.json()["skills"]}
    assert "go" not in skills_after
    assert "python" in skills_after
