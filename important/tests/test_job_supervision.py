import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job, User, UserApplication
from src.app.repositories.job_supervision import (
    update_job_supervision,
    toggle_job_active,
    delete_job_safely,
)


@pytest.fixture
def test_setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        country = Country(id=1, name="Morocco", code="MA")
        company = Company(id=1, name="Acme Corp", website_url="https://acme.org", active=True)
        session.add_all([country, company])
        session.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        job1 = Job(
            id=101,
            company_id=1,
            country_id=1,
            title="Old Backend Title",
            location="Casablanca",
            department="IT",
            job_url="https://acme.org/jobs/101",
            active=True,
            discovered_at=now,
            created_at=now,
            updated_at=now,
        )
        job2 = Job(
            id=102,
            company_id=1,
            country_id=1,
            title="Junior Analyst",
            location="Rabat",
            job_url="https://acme.org/jobs/102",
            active=True,
            discovered_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add_all([job1, job2])
        session.commit()

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    yield session_factory, client

    app.dependency_overrides.clear()


def test_repository_job_supervision(test_setup):
    session_factory, _ = test_setup
    with session_factory() as session:
        # 1. Update job supervision
        updated = update_job_supervision(
            session,
            101,
            title="Senior Lead Backend Architect",
            remote_type="Hybrid",
            employment_type="Full-time",
            location="Casablanca Marina",
        )
        assert updated is not None
        assert updated.title == "Senior Lead Backend Architect"
        assert updated.remote_type == "Hybrid"
        assert updated.location == "Casablanca Marina"

        # 2. Toggle active
        toggled = toggle_job_active(session, 101)
        assert toggled.active is False
        toggled_again = toggle_job_active(session, 101)
        assert toggled_again.active is True

        # 3. Delete without applications -> hard delete
        deleted = delete_job_safely(session, 102, force=False)
        assert deleted is True
        remaining = session.query(Job).filter(Job.id == 102).first()
        assert remaining is None


def test_job_supervision_safe_deletion_with_applications(test_setup):
    session_factory, _ = test_setup
    with session_factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user = User(id=1, email="test@job.com", password_hash="pw", is_active=True, created_at=now, updated_at=now)
        session.add(user)
        session.flush()
        app_entry = UserApplication(id=1, user_id=1, job_id=101, status="applied", created_at=now, updated_at=now)
        session.add(app_entry)
        session.commit()

        # Delete without force -> soft deactivates
        deleted = delete_job_safely(session, 101, force=False)
        assert deleted is True

        job = session.query(Job).filter(Job.id == 101).first()
        assert job is not None
        assert job.active is False  # Safely soft deactivated!

        # Now force delete -> removes job and applications
        force_deleted = delete_job_safely(session, 101, force=True)
        assert force_deleted is True
        job_after = session.query(Job).filter(Job.id == 101).first()
        assert job_after is None


def test_job_supervision_api_endpoints(test_setup):
    _, client = test_setup

    # Register user to get JWT token
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "supervisor@test.com", "password": "Password123!"},
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Patch job
    patch_resp = client.patch(
        "/api/v1/admin/jobs/101",
        headers=headers,
        json={
            "title": "Supervised Staff Platform Engineer",
            "remote_type": "Remote",
            "active": False,
        },
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["title"] == "Supervised Staff Platform Engineer"
    assert data["remote_type"] == "Remote"
    assert data["active"] is False

    # Get all jobs with active_only=false to see the deactivated job
    all_jobs_resp = client.get("/api/v1/jobs?active_only=false")
    assert all_jobs_resp.status_code == 200
    all_items = all_jobs_resp.json()["items"]
    j101 = next(j for j in all_items if j["id"] == 101)
    assert j101["active"] is False

    # Delete job
    del_resp = client.delete("/api/v1/admin/jobs/101", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"


def test_job_search_by_company_name(test_setup):
    _, client = test_setup

    # Search by company name "Acme"
    resp = client.get("/api/v1/jobs?search=Acme&active_only=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert any(j["id"] == 101 for j in data["items"])
    assert any(j["id"] == 102 for j in data["items"])
    assert all(j["company_name"] == "Acme Corp" for j in data["items"])

    # Search for nonexistent company
    resp_none = client.get("/api/v1/jobs?search=NonExistentCompany999&active_only=false")
    assert resp_none.status_code == 200
    assert resp_none.json()["total"] == 0


def test_job_supervision_bulk_delete_api(test_setup):
    session_factory, client = test_setup

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "bulk_supervisor@test.com", "password": "Password123!"},
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add application to job 101 so 101 is soft-deactivated and 102 is hard-deleted
    with session_factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user = User(id=99, email="candidate@test.com", password_hash="pw", is_active=True, created_at=now, updated_at=now)
        session.add(user)
        session.flush()
        app_entry = UserApplication(id=99, user_id=99, job_id=101, status="applied", created_at=now, updated_at=now)
        session.add(app_entry)
        session.commit()

    # Bulk delete [101, 102] with force=False
    bulk_resp = client.post(
        "/api/v1/admin/jobs/bulk-delete",
        headers=headers,
        json={"job_ids": [101, 102], "force": False},
    )
    assert bulk_resp.status_code == 200
    res = bulk_resp.json()
    assert res["status"] == "success"
    assert res["deleted_count"] == 1  # job 102 hard-deleted
    assert res["deactivated_count"] == 1  # job 101 soft-deactivated
    assert res["total_requested"] == 2

    with session_factory() as session:
        j102 = session.query(Job).filter(Job.id == 102).first()
        assert j102 is None
        j101 = session.query(Job).filter(Job.id == 101).first()
        assert j101 is not None
        assert j101.active is False

    # Now force bulk delete [101]
    force_resp = client.post(
        "/api/v1/admin/jobs/bulk-delete",
        headers=headers,
        json={"job_ids": [101], "force": True},
    )
    assert force_resp.status_code == 200
    assert force_resp.json()["deleted_count"] == 1

    with session_factory() as session:
        assert session.query(Job).filter(Job.id == 101).first() is None
