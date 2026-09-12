from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, User, UserSkill, UserExperience, UserEducation, UserLanguage, Resume
from src.app.security import create_access_token


@pytest.fixture
def test_env():
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
            phone="+212 600-112233",
            created_at=now,
            updated_at=now,
        )
        user2 = User(
            id=2,
            email="other@compust.ai",
            password_hash="pw",
            is_active=True,
            first_name="Sarah",
            last_name="Connor",
            created_at=now,
            updated_at=now,
        )
        session.add_all([user1, user2])
        session.flush()

        # Add profile data to user1
        session.add(UserSkill(user_id=1, skill="Python", proficiency="Expert"))
        session.add(UserSkill(user_id=1, skill="FastAPI", proficiency="Advanced"))
        session.add(UserExperience(
            user_id=1,
            title="Senior Backend Engineer",
            company_name="Tech Solutions",
            description="Built scalable microservices and APIs.",
        ))
        session.add(UserEducation(
            user_id=1,
            institution="Universite Hassan II",
            degree="Master",
            field_of_study="Computer Science",
        ))
        session.add(UserLanguage(user_id=1, language="French", proficiency="Native"))

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


def test_resume_crud_lifecycle(test_env):
    client, token1, _ = test_env
    headers = {"Authorization": f"Bearer {token1}"}

    # 1. Create a new structured resume
    create_resp = client.post(
        "/api/v1/resumes",
        headers=headers,
        json={
            "title": "Software Engineering Resume",
            "is_default": True,
            "structured_data": {
                "profile": {
                    "full_name": "Amine El Amrani",
                    "headline": "Lead Python Engineer",
                    "email": "candidate@compust.ai",
                    "phone": "+212 600-112233",
                    "summary": "10+ years engineering scalable systems.",
                },
                "skills": [{"id": "s1", "name": "Python", "category": "Backend", "proficiency": "Expert"}],
                "experience": [],
                "education": [],
                "projects": [],
                "certifications": [],
                "languages": [],
                "custom_sections": [],
            },
            "settings": {
                "template": "modern",
                "theme_color": "#0ea5e9",
                "font_family": "Inter",
                "font_size": "10.5",
                "document_size": "A4",
            },
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    resume_id = created["id"]
    assert created["title"] == "Software Engineering Resume"
    assert created["is_default"] is True
    assert created["structured_data"]["profile"]["headline"] == "Lead Python Engineer"

    # 2. List resumes
    list_resp = client.get("/api/v1/resumes", headers=headers)
    assert list_resp.status_code == 200
    resumes = list_resp.json()
    assert len(resumes) >= 1
    assert any(r["id"] == resume_id for r in resumes)

    # 3. Update resume
    update_resp = client.put(
        f"/api/v1/resumes/{resume_id}",
        headers=headers,
        json={
            "title": "Principal Architect Resume",
            "structured_data": {
                "profile": {
                    "full_name": "Amine El Amrani",
                    "headline": "Principal Architect",
                    "summary": "Updated summary.",
                },
                "skills": [
                    {"id": "s1", "name": "Python", "category": "Backend", "proficiency": "Expert"},
                    {"id": "s2", "name": "Docker", "category": "DevOps", "proficiency": "Advanced"},
                ],
                "experience": [],
                "education": [],
                "projects": [],
                "certifications": [],
                "languages": [],
                "custom_sections": [],
            },
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["title"] == "Principal Architect Resume"
    assert len(updated["structured_data"]["skills"]) == 2

    # 4. Duplicate resume
    dup_resp = client.post(
        f"/api/v1/resumes/{resume_id}/duplicate",
        headers=headers,
        json={"new_title": "Duplicated Architect Resume"},
    )
    assert dup_resp.status_code == 200
    duplicated = dup_resp.json()
    assert duplicated["id"] != resume_id
    assert duplicated["title"] == "Duplicated Architect Resume"
    assert duplicated["source_resume_id"] == resume_id
    assert duplicated["is_default"] is False

    # 5. Set default
    def_resp = client.post(f"/api/v1/resumes/{duplicated['id']}/set-default", headers=headers)
    assert def_resp.status_code == 200
    assert def_resp.json()["is_default"] is True

    # Verify previous is no longer default
    orig_check = client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert orig_check.json()["is_default"] is False

    # 6. Delete duplicate
    del_resp = client.delete(f"/api/v1/resumes/{duplicated['id']}", headers=headers)
    assert del_resp.status_code == 200


def test_import_profile_into_resume(test_env):
    client, token1, _ = test_env
    headers = {"Authorization": f"Bearer {token1}"}

    create_resp = client.post(
        "/api/v1/resumes",
        headers=headers,
        json={"title": "Empty Resume", "is_default": False},
    )
    resume_id = create_resp.json()["id"]

    # Import profile data
    import_resp = client.post(f"/api/v1/resumes/{resume_id}/import-profile", headers=headers)
    assert import_resp.status_code == 200
    imported = import_resp.json()

    s_data = imported["structured_data"]
    # Verify profile skills imported
    skill_names = [s["name"] for s in s_data.get("skills", [])]
    assert "Python" in skill_names
    assert "FastAPI" in skill_names

    # Verify experience imported
    exp_companies = [e["company"] for e in s_data.get("experience", [])]
    assert "Tech Solutions" in exp_companies

    # Verify education imported
    edu_insts = [ed["institution"] for ed in s_data.get("education", [])]
    assert "Universite Hassan II" in edu_insts

    # Verify language imported
    langs = [l["language"] for l in s_data.get("languages", [])]
    assert "French" in langs


def test_cross_user_isolation(test_env):
    client, token1, token2 = test_env
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 1 creates resume
    res1 = client.post(
        "/api/v1/resumes",
        headers=headers1,
        json={"title": "User 1 Secret Resume"},
    ).json()

    # User 2 attempts to view User 1's resume -> 404
    view_resp = client.get(f"/api/v1/resumes/{res1['id']}", headers=headers2)
    assert view_resp.status_code == 404

    # User 2 attempts to update User 1's resume -> 404
    upd_resp = client.put(
        f"/api/v1/resumes/{res1['id']}",
        headers=headers2,
        json={"title": "Hacked Title"},
    )
    assert upd_resp.status_code == 404

    # User 2 attempts to delete User 1's resume -> 404
    del_resp = client.delete(f"/api/v1/resumes/{res1['id']}", headers=headers2)
    assert del_resp.status_code == 404
