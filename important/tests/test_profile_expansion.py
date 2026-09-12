from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.matching.matcher import calculate_job_match
from src.app.models import Base, Job, User, UserExperience, UserLanguage
from src.app.repositories.auth import create_user
from src.app.schemas_auth import UserRegisterRequest


def test_profile_endpoints_experience_education_and_languages() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    # 1. Register candidate
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "salma@example.com",
            "password": "Password123!",
            "first_name": "Salma",
            "last_name": "Bennani",
        },
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify initial empty profile
    me_resp = client.get("/api/v1/profile", headers=headers)
    assert me_resp.status_code == 200
    profile = me_resp.json()
    assert profile["experience"] == []
    assert profile["education"] == []
    assert profile["languages"] == []

    # 3. Add professional experience
    exp1_resp = client.post(
        "/api/v1/profile/experiences",
        headers=headers,
        json={
            "title": "Lead Software Engineer",
            "company_name": "Tech Corp",
            "experience_type": "professional",
            "start_date": "2021-01-01",
            "end_date": "2024-01-01",
            "description": "Architected distributed cloud platforms.",
        },
    )
    assert exp1_resp.status_code == 201
    assert len(exp1_resp.json()["experience"]) == 1
    exp1_id = exp1_resp.json()["experience"][0]["id"]
    assert exp1_resp.json()["experience"][0]["experience_type"] == "professional"

    # Add internship experience
    exp2_resp = client.post(
        "/api/v1/profile/experiences",
        headers=headers,
        json={
            "title": "Software Engineering Intern",
            "company_name": "Startup Studio",
            "experience_type": "internship",
            "start_date": "2020-06-01",
            "end_date": "2020-09-01",
        },
    )
    assert exp2_resp.status_code == 201
    experiences = exp2_resp.json()["experience"]
    assert len(experiences) == 2
    types = {e["experience_type"] for e in experiences}
    assert types == {"professional", "internship"}

    # Delete internship
    exp2_id = [e["id"] for e in experiences if e["id"] != exp1_id][0]
    del_exp_resp = client.delete(f"/api/v1/profile/experiences/{exp2_id}", headers=headers)
    assert del_exp_resp.status_code == 200
    assert len(del_exp_resp.json()["experience"]) == 1
    assert del_exp_resp.json()["experience"][0]["id"] == exp1_id

    # 404 for invalid experience delete
    assert client.delete("/api/v1/profile/experiences/99999", headers=headers).status_code == 404

    # 4. Add Education
    edu_resp = client.post(
        "/api/v1/profile/educations",
        headers=headers,
        json={
            "institution": "EMI Rabat",
            "degree": "State Engineering Degree",
            "field_of_study": "Computer Engineering",
            "start_date": "2017-09-01",
            "end_date": "2020-06-30",
        },
    )
    assert edu_resp.status_code == 201
    assert len(edu_resp.json()["education"]) == 1
    edu_id = edu_resp.json()["education"][0]["id"]
    assert edu_resp.json()["education"][0]["institution"] == "EMI Rabat"

    # Delete Education
    del_edu_resp = client.delete(f"/api/v1/profile/educations/{edu_id}", headers=headers)
    assert del_edu_resp.status_code == 200
    assert len(del_edu_resp.json()["education"]) == 0
    assert client.delete("/api/v1/profile/educations/99999", headers=headers).status_code == 404

    # 5. Add Languages
    lang_resp1 = client.post(
        "/api/v1/profile/languages",
        headers=headers,
        json={"language": "French", "proficiency": "native"},
    )
    assert lang_resp1.status_code == 201
    assert len(lang_resp1.json()["languages"]) == 1

    lang_resp2 = client.post(
        "/api/v1/profile/languages",
        headers=headers,
        json={"language": "English", "proficiency": "fluent"},
    )
    assert lang_resp2.status_code == 201
    assert len(lang_resp2.json()["languages"]) == 2

    # Upsert language (updating proficiency for existing language)
    lang_resp3 = client.post(
        "/api/v1/profile/languages",
        headers=headers,
        json={"language": "English", "proficiency": "native"},
    )
    assert lang_resp3.status_code == 201
    langs = lang_resp3.json()["languages"]
    assert len(langs) == 2
    eng = [l for l in langs if l["language"] == "english"][0]
    assert eng["proficiency"] == "native"

    # Delete Language
    del_lang_resp = client.delete(f"/api/v1/profile/languages/{eng['id']}", headers=headers)
    assert del_lang_resp.status_code == 200
    assert len(del_lang_resp.json()["languages"]) == 1
    assert client.delete("/api/v1/profile/languages/99999", headers=headers).status_code == 404


def test_matching_engine_distinguishes_experience_types() -> None:
    now = datetime.now()

    # Candidate with only internships
    intern_candidate = User(
        id=1,
        email="intern@test.com",
        password_hash="pw",
        created_at=now,
        updated_at=now,
        email_verified=True,
        is_active=True,
    )
    intern_candidate.skills = []
    intern_candidate.experience = [
        UserExperience(
            id=1,
            user_id=1,
            title="Backend Engineering Intern",
            company_name="Alpha Inc",
            experience_type="internship",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 9, 1),
        ),
        UserExperience(
            id=2,
            user_id=1,
            title="Full Stack Intern",
            company_name="Beta Labs",
            experience_type="internship",
            start_date=date(2022, 6, 1),
            end_date=date(2022, 9, 1),
        ),
    ]
    intern_candidate.languages = [
        UserLanguage(id=1, user_id=1, language="french", proficiency="fluent")
    ]

    # Candidate with 4 years full-time professional experience
    senior_candidate = User(
        id=2,
        email="senior@test.com",
        password_hash="pw",
        created_at=now,
        updated_at=now,
        email_verified=True,
        is_active=True,
    )
    senior_candidate.skills = []
    senior_candidate.experience = [
        UserExperience(
            id=3,
            user_id=2,
            title="Senior Backend Engineer",
            company_name="Gamma Cloud",
            experience_type="professional",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 1, 1),
        )
    ]
    senior_candidate.languages = [
        UserLanguage(id=2, user_id=2, language="french", proficiency="native")
    ]

    senior_job = Job(
        id=101,
        company_id=1,
        country_id=1,
        title="Senior Cloud Engineer",
        job_url="https://example.com/job/101",
        description="We are seeking an experienced engineer. Fluent in French required.",
        active=True,
        discovered_at=now,
        created_at=now,
        updated_at=now,
    )

    junior_job = Job(
        id=102,
        company_id=1,
        country_id=1,
        title="Junior Backend Developer",
        job_url="https://example.com/job/102",
        description="Entry-level opening for graduates or internship alumni.",
        active=True,
        discovered_at=now,
        created_at=now,
        updated_at=now,
    )

    # 1. Senior job against Intern: should note missing tenure / senior requirement
    intern_senior_match = calculate_job_match(senior_job, [], intern_candidate)
    assert any("Senior roles require substantive professional career tenure" in f for f in intern_senior_match.missing_factors)
    assert any("Satisfies language requirement" in f for f in intern_senior_match.positive_factors)

    # 2. Senior job against Senior: meets seniority requirement
    senior_match = calculate_job_match(senior_job, [], senior_candidate)
    assert any("Meets seniority requirement" in f for f in senior_match.positive_factors)
    assert senior_match.score > intern_senior_match.score

    # 3. Junior job against Intern: internship experience aligns positively with entry role
    intern_junior_match = calculate_job_match(junior_job, [], intern_candidate)
    assert any("portfolio strongly aligns with entry-level position" in f for f in intern_junior_match.positive_factors)
