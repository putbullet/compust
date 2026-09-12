from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, ScrapeTarget, ScrapingRun


def test_scraper_metrics_endpoint() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        comp = Company(id=1, name="Metrics Corp", website_url="https://metrics.test", active=True)
        session.add(comp)
        session.flush()

        t1 = ScrapeTarget(id=1, company_id=1, url="https://metrics.test/jobs", active=True, robots_txt_allowed=True)
        t2 = ScrapeTarget(id=2, company_id=1, url="https://metrics.test/blocked", active=False, robots_txt_allowed=False)
        session.add_all([t1, t2])

        now = datetime.now()
        r1 = ScrapingRun(
            id=1,
            company_id=1,
            status="success",
            started_at=now - timedelta(seconds=10),
            finished_at=now,
            jobs_found=20,
            jobs_added=15,
            jobs_updated=5,
        )
        r2 = ScrapingRun(
            id=2,
            company_id=1,
            status="failed",
            started_at=now - timedelta(seconds=5),
            finished_at=now,
            jobs_found=0,
            jobs_added=0,
            jobs_updated=0,
            error_message="HTTP 500 server error",
        )
        session.add_all([r1, r2])
        session.commit()

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    resp = client.get("/api/v1/admin/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] == 2
    assert data["runs_by_status"]["success"] == 1
    assert data["runs_by_status"]["failed"] == 1
    assert data["success_rate_percent"] == 50.0
    assert data["avg_duration_seconds"] > 0
    assert data["total_jobs_found"] == 20
    assert data["total_jobs_added"] == 15
    assert data["total_jobs_updated"] == 5
    assert data["duplicate_rate_percent"] == 25.0
    assert data["total_targets"] == 2
    assert data["active_targets"] == 1
    assert data["robots_blocked_targets"] == 1
    assert len(data["recent_errors"]) == 1
    assert "HTTP 500" in data["recent_errors"][0]["error"]
