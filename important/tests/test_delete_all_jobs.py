from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job, User, UserApplication
from src.app.security import create_access_token


@pytest.fixture
def clean_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with session_factory() as session:
        user = User(
            id=1,
            email="admin@compust.ai",
            password_hash="pw",
            is_active=True,
            first_name="Admin",
            last_name="Compust",
            created_at=now,
            updated_at=now,
        )
        country = Country(id=1, name="Morocco", code="MA")
        company = Company(id=1, name="TechCorp", website_url="https://techcorp.com", active=True)
        session.add_all([user, country, company])
        session.commit()

    yield session_factory
    app.dependency_overrides.clear()


def test_delete_all_jobs_requires_confirmation_token(clean_db):
    client = TestClient(app)
    token = create_access_token(data={"sub": "admin@compust.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/admin/jobs/delete-all",
        json={"confirmation": "WRONG_TOKEN"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "DELETE" in res.json()["detail"]


def test_delete_all_jobs_safely_preserves_tracked_applications(clean_db):
    session_factory = clean_db
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with session_factory() as session:
        # Job 1: Untracked
        job_untracked = Job(
            id=101,
            company_id=1,
            country_id=1,
            title="Untracked Backend Dev",
            job_url="https://example.com/job/101",
            active=True,
            discovered_at=now,
            created_at=now,
            updated_at=now,
        )
        # Job 2: Tracked with user application
        job_tracked = Job(
            id=102,
            company_id=1,
            country_id=1,
            title="Tracked Lead Dev",
            job_url="https://example.com/job/102",
            active=True,
            discovered_at=now,
            created_at=now,
            updated_at=now,
        )
        user_app = UserApplication(
            id=1,
            user_id=1,
            job_id=102,
            status="applied",
            applied_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add_all([job_untracked, job_tracked, user_app])
        session.commit()

    client = TestClient(app)
    token = create_access_token(data={"sub": "admin@compust.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/admin/jobs/delete-all",
        json={"confirmation": "DELETE", "force_tracked": False},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["deleted_count"] == 1
    assert data["preserved_tracked_count"] == 1

    with session_factory() as session:
        # Untracked job is deleted
        check_untracked = session.scalar(select(Job).where(Job.id == 101))
        assert check_untracked is None

        # Tracked job is preserved (soft-deactivated)
        check_tracked = session.scalar(select(Job).where(Job.id == 102))
        assert check_tracked is not None
        assert check_tracked.active is False

        # User application is completely intact
        check_app = session.scalar(select(UserApplication).where(UserApplication.id == 1))
        assert check_app is not None
