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
    assert "total_jobs_detected" in data
    assert "rejection_reasons" in data

    app.dependency_overrides.clear()


@patch("src.app.scraper.diagnostics.crawl_pages")
def test_scraper_diagnostics_discrepancy_and_rejection_tracking(mock_crawl):
    valid_job = JobCandidate(
        title="Full Stack Developer",
        job_url="https://example.com/careers/job1",
        external_job_id="valid-1",
        location="Casablanca",
        description="Valid description",
    )
    generic_job = JobCandidate(
        title="About Us",
        job_url="https://example.com/about",
        external_job_id="generic-2",
    )
    missing_title_job = JobCandidate(
        title="",
        job_url="https://example.com/jobs/empty",
        external_job_id="empty-3",
    )
    mock_crawl.return_value = CrawlResult(
        jobs=[valid_job, generic_job, missing_title_job],
        errors=[],
        pages_crawled=2,
        stop_reason="max_pages_reached",
        content_signal_count=18,
    )

    report = run_scraper_diagnostics("https://example.com/careers", max_pages=2)

    assert report.total_jobs_detected == 3
    assert report.jobs_accepted == 1
    assert report.jobs_rejected == 2
    assert "generic_title" in report.rejection_reasons
    assert "missing_title" in report.rejection_reasons
    assert report.content_signal_count == 18
    assert report.discrepancy_detected is True
    assert "Page content signal detected" in (report.discrepancy_details or "")
    assert len(report.rejected_items) == 2


def test_scraper_assistant_deterministic_explanation():
    from src.app.services.scraper_assistant import explain_scraper_run

    report_dict = {
        "target_url": "https://example.com/careers",
        "strategy_used": "universal",
        "platform_detected": "unknown",
        "status": "PARTIAL_SUCCESS",
        "pages_crawled": 3,
        "max_pages": 3,
        "stop_reason": "max_pages_reached",
        "content_signal_count": 25,
        "total_jobs_detected": 4,
        "jobs_accepted": 1,
        "jobs_rejected": 3,
        "rejection_reasons": {"generic_title": 2, "missing_title": 1},
        "discrepancy_detected": True,
        "discrepancy_details": "Raw HTML contains 25 job card markers, but universal parser extracted only 4 candidates.",
        "rejected_items": [{"title": "Contact", "url": "https://example.com/contact", "reason": "generic_title"}],
        "errors": [],
    }

    # Force offline Ollama
    with patch("src.app.services.scraper_assistant.check_ollama_runtime") as mock_runtime:
        mock_runtime.return_value = {"status": "unavailable", "models": []}
        explanation = explain_scraper_run(report_dict)

    assert explanation["provider"] == "deterministic"
    assert "universal" in explanation["summary"]
    assert "Discrepancy Warning" in explanation["discrepancy_explanation"]
    assert "generic_title" in explanation["reasons_breakdown"]
    assert len(explanation["recommendations"]) > 0


def test_apply_scraper_decision_keep_and_force():
    from src.app.services.scraper_assistant import apply_scraper_decision
    from src.app.models import Job, Company, Country

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        # Seed country
        country = Country(name="Morocco", code="MA")
        db.add(country)
        db.commit()

        # Decision 1: keep_accepted
        res_keep = apply_scraper_decision(
            db,
            target_url="https://company.com/careers",
            decision="keep_accepted",
            rejected_items=[{"title": "Filtered Lead", "url": "https://company.com/jobs/1"}],
        )
        assert res_keep["action"] == "keep_accepted"
        assert res_keep["integrated_count"] == 0
        assert db.query(Job).count() == 0

        # Decision 2: force_integrate_all
        res_force = apply_scraper_decision(
            db,
            target_url="https://company.com/careers",
            decision="force_integrate_all",
            rejected_items=[
                {"title": "Senior Engineer", "url": "https://company.com/jobs/10", "company": "Acme Inc"},
                {"title": "Marketing Manager", "url": "https://company.com/jobs/20", "company": "Acme Inc"},
            ],
        )
        assert res_force["action"] == "force_integrate_all"
        assert res_force["integrated_count"] == 2
        assert db.query(Job).count() == 2
        jobs = db.query(Job).all()
        titles = [j.title for j in jobs]
        assert "Senior Engineer" in titles
        assert "Marketing Manager" in titles

