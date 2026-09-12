from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job, JobSkill, ScrapingRun


@pytest.fixture
def test_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_list_and_detail_jobs_api(test_db) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    country1 = Country(id=1, name="Morocco", code="MA")
    country2 = Country(id=2, name="France", code="FR")
    company1 = Company(id=1, name="Orange", website_url="https://orange.ma", careers_url=None, active=True)
    company2 = Company(id=2, name="Inwi", website_url="https://inwi.ma", careers_url=None, active=True)
    test_db.add_all([country1, country2, company1, company2])
    test_db.flush()

    job1 = Job(
        id=1,
        company_id=1,
        country_id=1,
        title="Python Backend Engineer",
        location="Casablanca",
        job_url="https://example.com/job/1",
        description="Build scalable APIs",
        employment_type="CDI",
        remote_type="Hybrid",
        department="IT",
        discovered_at=now,
        created_at=now,
        updated_at=now,
        active=True,
    )
    job2 = Job(
        id=2,
        company_id=2,
        country_id=2,
        title="DevOps Specialist",
        location="Paris",
        job_url="https://example.com/job/2",
        description="Manage Kubernetes clusters",
        employment_type="CDD",
        remote_type="Remote",
        department="Infrastructure",
        discovered_at=now,
        created_at=now,
        updated_at=now,
        active=True,
    )
    test_db.add_all([job1, job2])
    test_db.flush()

    skill1 = JobSkill(job_id=1, skill="Python")
    skill2 = JobSkill(job_id=1, skill="FastAPI")
    test_db.add_all([skill1, skill2])
    test_db.commit()

    def override_db():
        yield test_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    try:
        # 1. List all jobs
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # 2. Filter by country
        resp_ma = client.get("/api/v1/jobs?country_id=1")
        assert resp_ma.status_code == 200
        assert resp_ma.json()["total"] == 1
        assert resp_ma.json()["items"][0]["id"] == 1

        # 3. Filter by search keyword
        resp_search = client.get("/api/v1/jobs?search=Kubernetes")
        assert resp_search.status_code == 200
        assert resp_search.json()["total"] == 1
        assert resp_search.json()["items"][0]["id"] == 2

        # 4. Filter by remote type
        resp_remote = client.get("/api/v1/jobs?remote_type=Hybrid")
        assert resp_remote.status_code == 200
        assert resp_remote.json()["total"] == 1
        assert resp_remote.json()["items"][0]["id"] == 1

        # 5. Get job detail with skills
        detail_resp = client.get("/api/v1/jobs/1")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["title"] == "Python Backend Engineer"
        assert set(detail_data["skills"]) == {"Python", "FastAPI"}

        # 6. Get non-existent job
        missing_resp = client.get("/api/v1/jobs/9999")
        assert missing_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
