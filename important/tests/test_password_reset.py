"""
Tests for the local password reset flow.
Verifies:
- reset-password endpoint works for valid email
- 404 is returned for unknown email
- Login with new password succeeds after reset
- Login with old password fails after reset
- All existing user data (applications, skills, etc.) remains intact post-reset
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, User, UserSkill, UserPreference


@pytest.fixture()
def client_with_user():
    """TestClient fixture with an in-memory SQLite DB and a pre-seeded user."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    # Register a user so we have a known password hash
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "OriginalPassword1!",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.json()}"

    # Seed some skills and preferences to validate data integrity post-reset
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    skills_resp = client.put(
        "/api/v1/profile/skills",
        headers=headers,
        json={"skills": ["Python", "FastAPI", "Docker", "SQL"]},
    )
    assert skills_resp.status_code == 200

    prefs_resp = client.put(
        "/api/v1/profile/preferences",
        headers=headers,
        json={
            "preferred_work_mode": "Remote",
            "preferred_location": "Casablanca",
            "min_salary": 25000.0,
            "salary_currency": "MAD",
        },
    )
    assert prefs_resp.status_code == 200

    yield client, token

    app.dependency_overrides.clear()
    engine.dispose()


def test_reset_password_valid_email(client_with_user):
    """Reset password for a known email succeeds and returns a valid token."""
    client, _ = client_with_user

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "testuser@example.com", "new_password": "BrandNew$ecret2!"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "testuser@example.com"
    assert data["user"]["first_name"] == "Test"


def test_reset_password_unknown_email(client_with_user):
    """Reset password for an unknown email returns 404."""
    client, _ = client_with_user

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "nobody@nowhere.com", "new_password": "SomePassword1!"},
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.json()}"
    assert "No account found" in resp.json()["detail"]


def test_login_with_new_password_after_reset(client_with_user):
    """After a password reset, user can log in with the new password."""
    client, _ = client_with_user

    # Reset the password
    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "testuser@example.com", "new_password": "MyNewPassword99!"},
    )
    assert reset_resp.status_code == 200

    # Login with new password
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "MyNewPassword99!"},
    )
    assert login_resp.status_code == 200, f"Login with new password failed: {login_resp.json()}"
    assert "access_token" in login_resp.json()


def test_old_password_fails_after_reset(client_with_user):
    """After a password reset, the old password no longer works."""
    client, _ = client_with_user

    # Reset the password
    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "testuser@example.com", "new_password": "ChangedPassword88!"},
    )
    assert reset_resp.status_code == 200

    # Try the old password — must fail
    old_login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "OriginalPassword1!"},
    )
    assert old_login_resp.status_code == 401, (
        f"Expected 401 for old password, got {old_login_resp.status_code}: {old_login_resp.json()}"
    )


def test_existing_skills_intact_after_reset(client_with_user):
    """User skills are preserved after a password reset."""
    client, _ = client_with_user

    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "testuser@example.com", "new_password": "AnotherNewPwd1!"},
    )
    assert reset_resp.status_code == 200

    new_token = reset_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {new_token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    profile = me_resp.json()
    assert set(profile["skills"]) == {"Python", "FastAPI", "Docker", "SQL"}, (
        f"Skills changed after reset: {profile['skills']}"
    )


def test_existing_preferences_intact_after_reset(client_with_user):
    """User preferences are preserved after a password reset."""
    client, _ = client_with_user

    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "testuser@example.com", "new_password": "FreshCreds2026!"},
    )
    assert reset_resp.status_code == 200

    new_token = reset_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {new_token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    prefs = me_resp.json().get("preferences", {})
    assert prefs is not None, "Preferences were wiped after reset"
    assert prefs["preferred_work_mode"] == "Remote"
    assert prefs["preferred_location"] == "Casablanca"
    assert prefs["min_salary"] == 25000.0


def test_reset_password_then_use_returned_token(client_with_user):
    """The token returned by reset-password immediately authenticates the user."""
    client, _ = client_with_user

    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "testuser@example.com", "new_password": "InstantAuth777!"},
    )
    assert reset_resp.status_code == 200
    immediate_token = reset_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {immediate_token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "testuser@example.com"


def test_reset_password_rejects_short_password(client_with_user):
    """Passwords shorter than 6 characters are rejected by schema validation (422)."""
    client, _ = client_with_user

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "testuser@example.com", "new_password": "abc"},
    )
    # Pydantic min_length=6 causes a 422 Unprocessable Entity
    assert resp.status_code == 422, (
        f"Expected 422 for short password, got {resp.status_code}: {resp.json()}"
    )
