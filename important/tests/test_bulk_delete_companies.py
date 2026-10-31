from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import (
    Base,
    Company,
    Country,
    Job,
    User,
    UserApplication,
    ScrapeTarget,
    ScrapingRun,
    company_countries,
)
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
        session.add_all([user, country])
        session.commit()

    yield session_factory
    app.dependency_overrides.clear()


def test_delete_all_companies_requires_confirmation_token(clean_db):
    client = TestClient(app)
    token = create_access_token(data={"sub": "admin@compust.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/admin/companies/delete-all",
        json={"confirmation": "INCORRECT"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "DELETE" in res.json()["detail"]


def test_get_companies_scope_stats(clean_db):
    session_factory = clean_db
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with session_factory() as session:
        c1 = Company(id=10, name="Acme Corp", website_url="https://acme.com", active=True)
        c2 = Company(id=20, name="Beta LLC", website_url="https://beta.com", active=False)
        target = ScrapeTarget(id=1, company_id=10, url="https://acme.com/jobs", active=True)
        j1 = Job(id=1, company_id=10, country_id=1, title="Backend Dev", job_url="https://acme.com/1", active=True, created_at=now, updated_at=now, discovered_at=now, posted_at=now)
        j2 = Job(id=2, company_id=10, country_id=1, title="Frontend Dev", job_url="https://acme.com/2", active=True, created_at=now, updated_at=now, discovered_at=now, posted_at=now)
        app_item = UserApplication(id=1, user_id=1, job_id=1, status="applied", created_at=now, updated_at=now)
        session.add_all([c1, c2, target, j1, j2, app_item])
        session.commit()

    client = TestClient(app)
    token = create_access_token(data={"sub": "admin@compust.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/admin/companies/scope-stats",
        json={"search": "Acme"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_companies"] == 1
    assert data["total_jobs"] == 2
    assert data["protected_jobs"] == 1
    assert data["untracked_jobs"] == 1
    assert data["scrape_targets_count"] == 1


def test_delete_all_companies_default_preserves_and_archives_jobs(clean_db):
    session_factory = clean_db
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with session_factory() as session:
        c1 = Company(id=10, name="Acme Corp", website_url="https://acme.com", active=True)
        target = ScrapeTarget(id=1, company_id=10, url="https://acme.com/jobs", active=True)
        j1 = Job(id=1, company_id=10, country_id=1, title="Backend Dev", job_url="https://acme.com/1", active=True, created_at=now, updated_at=now, discovered_at=now, posted_at=now)
        j2 = Job(id=2, company_id=10, country_id=1, title="Frontend Dev", job_url="https://acme.com/2", active=True, created_at=now, updated_at=now, discovered_at=now, posted_at=now)
        app_item = UserApplication(id=1, user_id=1, job_id=1, status="applied", created_at=now, updated_at=now)
        session.add_all([c1, target, j1, j2, app_item])
        session.commit()

    client = TestClient(app)
    token = create_access_token(data={"sub": "admin@compust.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    mock_backup = MagicMock(filename="test_backup_2026.zip")
    with patch("src.app.repositories.companies.data_manager_service.export_backup", return_value=mock_backup):
        res = client.post(
            "/api/v1/admin/companies/delete-all",
            json={
                "confirmation": "DELETE",
                "company_ids": [10],
                "delete_untracked_jobs": False,
            },
            headers=headers,
        )
    assert res.status_code == 200
    data = res.json()
    assert data["deleted_companies_count"] == 1
    assert data["deleted_targets_count"] == 1
    assert data["deleted_jobs_count"] == 0
    assert data["preserved_jobs_count"] == 2
    assert data["backup_filename"] == "test_backup_2026.zip"

    with session_factory() as session:
        assert session.scalar(select(Company).where(Company.id == 10)) is None
        assert session.scalar(select(ScrapeTarget).where(ScrapeTarget.id == 1)) is None
        archived = session.scalar(select(Company).where(Company.name == "[Archived Employer]"))
        assert archived is not None
        jobs = list(session.scalars(select(Job)).all())
        assert len(jobs) == 2
        for j in jobs:
            assert j.company_id == archived.id
            assert j.active is False
        app_check = session.scalar(select(UserApplication).where(UserApplication.id == 1))
        assert app_check is not None
        assert app_check.job_id == 1
        assert app_check.custom_company_name == "Acme Corp"


def test_delete_all_companies_removes_untracked_jobs_when_flag_enabled(clean_db):
    session_factory = clean_db
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with session_factory() as session:
        c1 = Company(id=10, name="Acme Corp", website_url="https://acme.com", active=True)
        j1 = Job(id=1, company_id=10, country_id=1, title="Tracked Job", job_url="https://acme.com/1", active=True, created_at=now, updated_at=now, discovered_at=now, posted_at=now)
        j2 = Job(id=2, company_id=10, country_id=1, title="Untracked Job", job_url="https://acme.com/2", active=True, created_at=now, updated_at=now, discovered_at=now, posted_at=now)
        app_item = UserApplication(id=1, user_id=1, job_id=1, status="saved", created_at=now, updated_at=now)
        session.add_all([c1, j1, j2, app_item])
        session.commit()

    client = TestClient(app)
    token = create_access_token(data={"sub": "admin@compust.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    mock_backup = MagicMock(filename="test_backup_2026.zip")
    with patch("src.app.repositories.companies.data_manager_service.export_backup", return_value=mock_backup):
        res = client.post(
            "/api/v1/admin/companies/delete-all",
            json={
                "confirmation": "DELETE",
                "company_ids": [10],
                "delete_untracked_jobs": True,
            },
            headers=headers,
        )
    assert res.status_code == 200
    data = res.json()
    assert data["deleted_companies_count"] == 1
    assert data["deleted_jobs_count"] == 1
    assert data["preserved_jobs_count"] == 1

    with session_factory() as session:
        assert session.scalar(select(Job).where(Job.id == 2)) is None
        preserved = session.scalar(select(Job).where(Job.id == 1))
        assert preserved is not None
        assert preserved.active is False
        app_check = session.scalar(select(UserApplication).where(UserApplication.id == 1))
        assert app_check.job_id == 1


def test_delete_all_companies_scoped_by_filter(clean_db):
    session_factory = clean_db

    with session_factory() as session:
        c1 = Company(id=10, name="Alpha Corp", website_url="https://alpha.com", active=True)
        c2 = Company(id=20, name="Beta Inc", website_url="https://beta.com", active=True)
        session.add_all([c1, c2])
        session.commit()

    client = TestClient(app)
    token = create_access_token(data={"sub": "admin@compust.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    mock_backup = MagicMock(filename="test_backup_2026.zip")
    with patch("src.app.repositories.companies.data_manager_service.export_backup", return_value=mock_backup):
        res = client.post(
            "/api/v1/admin/companies/delete-all",
            json={
                "confirmation": "DELETE",
                "search": "Beta",
            },
            headers=headers,
        )
    assert res.status_code == 200
    data = res.json()
    assert data["deleted_companies_count"] == 1

    with session_factory() as session:
        assert session.scalar(select(Company).where(Company.id == 20)) is None
        assert session.scalar(select(Company).where(Company.id == 10)) is not None


def test_delete_all_companies_large_volume(clean_db):
    session_factory = clean_db
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Seed 50 companies with targets, runs, and jobs
    with session_factory() as session:
        entities = []
        for i in range(100, 150):
            c = Company(id=i, name=f"BulkCo {i}", website_url=f"https://bulk{i}.com", active=True)
            t = ScrapeTarget(id=i, company_id=i, url=f"https://bulk{i}.com/careers", active=True)
            r = ScrapingRun(id=i, company_id=i, status="success", started_at=now, finished_at=now)
            j = Job(id=i, company_id=i, country_id=1, title=f"Job {i}", job_url=f"https://bulk{i}.com/job/{i}", active=True, created_at=now, updated_at=now, discovered_at=now, posted_at=now)
            entities.extend([c, t, r, j])
        # Track 5 of these jobs
        for i in range(100, 105):
            entities.append(UserApplication(id=i, user_id=1, job_id=i, status="saved", created_at=now, updated_at=now))
        session.add_all(entities)
        session.commit()

    client = TestClient(app)
    token = create_access_token(data={"sub": "admin@compust.ai"})
    headers = {"Authorization": f"Bearer {token}"}

    mock_backup = MagicMock(filename="large_vol_backup.zip")
    with patch("src.app.repositories.companies.data_manager_service.export_backup", return_value=mock_backup):
        res = client.post(
            "/api/v1/admin/companies/delete-all",
            json={
                "confirmation": "DELETE",
                "search": "BulkCo",
                "delete_untracked_jobs": True,
            },
            headers=headers,
        )
    assert res.status_code == 200
    data = res.json()
    assert data["deleted_companies_count"] == 50
    assert data["deleted_targets_count"] == 50
    assert data["deleted_jobs_count"] == 45
    assert data["preserved_jobs_count"] == 5

    with session_factory() as session:
        # All 50 companies gone
        remaining = list(session.scalars(select(Company).where(Company.id.between(100, 149))).all())
        assert len(remaining) == 0
        # Untracked jobs deleted
        assert session.scalar(select(Job).where(Job.id == 110)) is None
        # 5 protected jobs preserved
        for i in range(100, 105):
            pj = session.scalar(select(Job).where(Job.id == i))
            assert pj is not None
            assert pj.active is False
