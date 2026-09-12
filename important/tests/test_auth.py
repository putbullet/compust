from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base


def test_auth_registration_login_and_profile() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    # 1. Register user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "SecurePassword123!",
            "first_name": "Hamza",
            "last_name": "Alaoui",
        },
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "candidate@example.com"
    token = reg_data["access_token"]

    # 2. Duplicate registration fails
    dup_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "OtherPassword",
        },
    )
    assert dup_resp.status_code == 400

    # 3. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "candidate@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # 4. Invalid login fails
    bad_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "candidate@example.com",
            "password": "WrongPassword",
        },
    )
    assert bad_login.status_code == 401

    # 5. Access /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["first_name"] == "Hamza"

    # 6. Update preferences
    pref_resp = client.put(
        "/api/v1/profile/preferences",
        headers=headers,
        json={
            "preferred_work_mode": "Hybrid",
            "preferred_location": "Casablanca",
            "min_salary": 20000.0,
            "salary_currency": "MAD",
        },
    )
    assert pref_resp.status_code == 200
    assert pref_resp.json()["preferences"]["preferred_work_mode"] == "Hybrid"

    # 7. Update skills
    skills_resp = client.put(
        "/api/v1/profile/skills",
        headers=headers,
        json={"skills": ["Python", "FastAPI", "Docker"]},
    )
    assert skills_resp.status_code == 200
    assert "Python" in skills_resp.json()["skills"]

    app.dependency_overrides.clear()
    engine.dispose()
