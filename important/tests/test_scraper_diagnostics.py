import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base
from src.app.scraper.crawler import CrawlResult
from src.app.scraper.diagnostics import detect_target_platform, run_scraper_diagnostics
from src.app.scraper.orange_parser import JobCandidate


def test_detect_target_platform():
    assert detect_target_platform("https://boards.greenhouse.io/stripe") == "greenhouse"
    assert detect_target_platform("https://jobs.lever.co/figma") == "lever"
    assert detect_target_platform("https://careers.smartrecruiters.com/Acme") == "smartrecruiters"
    assert detect_target_platform("https://amazon.wd3.myworkdayjobs.com/Amazon_Jobs") == "workday"
    assert detect_target_platform("https://jobs.deloitte.com/search-jobs") == "deloitte"
    assert detect_target_platform("https://orange.jobs/careers") == "orange"
    assert detect_target_platform("https://example.com/careers") == "unknown"


@patch("src.app.scraper.diagnostics.crawl_pages")
def test_run_scraper_diagnostics_mock(mock_crawl):
    job1 = JobCandidate(
        title="Senior Cloud Architect",
        job_url="https://test.com/jobs/1",
        external_job_id="1",
        location="Casablanca",
        department="Cloud",
        description="Job description",
    )
    job2 = JobCandidate(
        title="Data Engineer",
        job_url="https://test.com/jobs/2",
        external_job_id="2",
        location="Rabat",
        department="Data",
        description="Job description",
    )
    mock_crawl.return_value = CrawlResult(jobs=[job1, job2], errors=[], pages_crawled=1)

    report = run_scraper_diagnostics(
        url="https://boards.greenhouse.io/test",
        max_pages=1,
    )

    assert report.target_url == "https://boards.greenhouse.io/test"
    assert report.platform_detected == "greenhouse"
    assert report.jobs_discovered == 2
    assert report.jobs_accepted == 2
    assert report.confidence_score == 1.0
    assert report.status == "SUCCESS"
    assert len(report.sample_jobs) == 2
    assert report.sample_jobs[0]["title"] == "Senior Cloud Architect"


@patch("src.app.scraper.diagnostics.crawl_pages")
def test_scraper_diagnostics_api_endpoint(mock_crawl):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    # Register supervisor
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "diag@compust.ai", "password": "Password123!"},
    )
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    job = JobCandidate(
        title="Solutions Engineer",
        job_url="https://jobs.lever.co/test/123",
        external_job_id="123",
        location="Remote",
        department="Sales",
        description="Description",
    )
    mock_crawl.return_value = CrawlResult(jobs=[job], errors=[], pages_crawled=1)

    res = client.post(
        "/api/v1/admin/scraper/test",
        headers=headers,
        json={"url": "https://jobs.lever.co/test", "max_pages": 1},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["target_url"] == "https://jobs.lever.co/test"
    assert data["platform_detected"] == "lever"
    assert data["jobs_accepted"] == 1
    assert data["status"] == "SUCCESS"

    app.dependency_overrides.clear()
