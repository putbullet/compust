from datetime import datetime, timezone
from pathlib import Path
import pytest
from src.app.scraper.http_client import FetchedSource
from src.app.scraper.registry import (
    UniversalScraperStrategy,
    AshbyScraperStrategy,
    WorkableScraperStrategy,
)
from src.app.scraper.platforms import AshbyAdapter, WorkableAdapter
from src.app.scraper.diagnostics import detect_target_platform, run_scraper_diagnostics

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def make_source(url: str, body: str, content_type: str = "text/html") -> FetchedSource:
    return FetchedSource(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type=content_type,
        body=body,
        fetched_at=datetime.now(timezone.utc),
    )


def test_rankly_media_fixture_parsing():
    fixture_path = FIXTURES_DIR / "rankly_media_careers.html"
    assert fixture_path.exists(), "Rankly Media fixture must exist"
    
    html = fixture_path.read_text(encoding="utf-8")
    source = make_source("https://ranklymedia.com/careers/", html, "text/html; charset=UTF-8")
    
    strategy = UniversalScraperStrategy()
    result = strategy.parse(source)
    
    assert not result.errors, f"Parsing errors: {result.errors}"
    assert len(result.jobs) == 4, f"Expected 4 jobs, got {len(result.jobs)}"
    
    titles = {j.title for j in result.jobs}
    expected_titles = {
        "SEO Specialist",
        "PPC / Paid Media Manager",
        "Web Developer (WordPress)",
        "Social Media & Content Creator",
    }
    assert expected_titles.issubset(titles), f"Missing titles: {expected_titles - titles}"
    
    for job in result.jobs:
        assert job.job_url, f"Missing job URL for {job.title}"
        assert "ranklymedia.com" in job.job_url
        assert job.location, f"Missing location for {job.title}"
        assert job.external_job_id, f"Missing external ID for {job.title}"


def test_secfix_ashby_fixture_parsing():
    fixture_path = FIXTURES_DIR / "ashby_secfix_api.json"
    assert fixture_path.exists(), "Ashby Secfix fixture must exist"
    
    json_text = fixture_path.read_text(encoding="utf-8")
    source = make_source("https://api.ashbyhq.com/posting-api/job-board/secfix", json_text, "application/json")
    
    adapter = AshbyAdapter()
    assert adapter.can_handle_url("https://jobs.ashbyhq.com/secfix")
    assert adapter.extract_organization("https://jobs.ashbyhq.com/secfix") == "secfix"
    assert adapter.resolve_fetch_url("https://jobs.ashbyhq.com/secfix") == "https://api.ashbyhq.com/posting-api/job-board/secfix"
    
    strategy = AshbyScraperStrategy()
    result = strategy.parse(source)
    
    assert not result.errors, f"Ashby errors: {result.errors}"
    assert len(result.jobs) == 16, f"Expected 16 jobs from Ashby fixture, got {len(result.jobs)}"
    
    job_titles = [j.title for j in result.jobs]
    assert any("Account Executive" in t for t in job_titles)
    assert any("Engineer" in t for t in job_titles)
    
    for job in result.jobs:
        assert job.title
        assert job.job_url
        assert job.external_job_id
        assert job.employment_type in ("full_time", "part_time", "contract", "internship", "other")


def test_riot_workable_fixture_parsing():
    fixture_path = FIXTURES_DIR / "workable_riot_widget.json"
    assert fixture_path.exists(), "Workable Riot fixture must exist"
    
    json_text = fixture_path.read_text(encoding="utf-8")
    source = make_source("https://apply.workable.com/api/v1/widget/accounts/riot", json_text, "application/json")
    
    adapter = WorkableAdapter()
    assert adapter.can_handle_url("https://apply.workable.com/riot/")
    assert adapter.extract_account_name("https://apply.workable.com/riot/") == "riot"
    assert adapter.resolve_fetch_url("https://apply.workable.com/riot/") == "https://apply.workable.com/api/v1/widget/accounts/riot"
    
    strategy = WorkableScraperStrategy()
    result = strategy.parse(source)
    
    assert not result.errors, f"Workable errors: {result.errors}"
    assert len(result.jobs) == 20, f"Expected 20 jobs from Riot widget fixture, got {len(result.jobs)}"
    
    for job in result.jobs:
        assert job.title
        assert job.job_url
        assert job.external_job_id
        assert "workable.com" in job.job_url


def test_universal_strategy_delegation_to_ats():
    strategy = UniversalScraperStrategy()
    
    # Ashby delegation
    ashby_url = "https://jobs.ashbyhq.com/secfix"
    assert strategy.resolve_fetch_url(ashby_url) == "https://api.ashbyhq.com/posting-api/job-board/secfix"
    
    # Workable delegation
    workable_url = "https://apply.workable.com/riot/"
    assert strategy.resolve_fetch_url(workable_url) == "https://apply.workable.com/api/v1/widget/accounts/riot"
    
    # Custom site remains unchanged
    custom_url = "https://ranklymedia.com/careers/"
    assert strategy.resolve_fetch_url(custom_url) == custom_url


def test_platform_detection_rules():
    assert detect_target_platform("https://jobs.ashbyhq.com/secfix") == "ashby"
    assert detect_target_platform("https://apply.workable.com/riot/") == "workable"
    assert detect_target_platform("https://boards.greenhouse.io/stripe") == "greenhouse"
    assert detect_target_platform("https://jobs.lever.co/figma") == "lever"
    assert detect_target_platform("https://careers.smartrecruiters.com/Acme") == "smartrecruiters"
    assert detect_target_platform("https://ranklymedia.com/careers/") == "unknown"


def test_diagnostic_spa_shell_detection():
    spa_html = """
    <!DOCTYPE html>
    <html>
      <head><title>Modern Careers SPA</title></head>
      <body>
        <noscript>You need to enable JavaScript to run this app.</noscript>
        <div id="root"></div>
      </body>
    </html>
    """
    source = make_source("https://example-spa.com/careers", spa_html, "text/html")
    strategy = UniversalScraperStrategy()
    res = strategy.parse(source)
    assert len(res.jobs) == 0
    assert any("Client-rendered SPA shell detected" in err for err in res.errors)


def test_live_rankly_media_discovery():
    report = run_scraper_diagnostics("https://ranklymedia.com/careers/", max_pages=1)
    assert report.status in ("SUCCESS", "PARTIAL_SUCCESS"), f"Expected success, got {report.status} with errors {report.errors}"
    assert report.jobs_discovered >= 4
    assert report.jobs_accepted >= 4
    titles = [j["title"] for j in report.sample_jobs]
    assert any("SEO" in t or "PPC" in t or "Developer" in t for t in titles)


def test_live_secfix_ashby_discovery():
    report = run_scraper_diagnostics("https://jobs.ashbyhq.com/secfix", max_pages=1)
    assert report.status in ("SUCCESS", "PARTIAL_SUCCESS"), f"Expected success, got {report.status} with errors {report.errors}"
    assert report.platform_detected == "ashby"
    assert report.jobs_discovered >= 10
    assert report.jobs_accepted >= 10


def test_live_riot_workable_discovery():
    report = run_scraper_diagnostics("https://apply.workable.com/riot/", max_pages=1)
    assert report.status in ("SUCCESS", "PARTIAL_SUCCESS"), f"Expected success, got {report.status} with errors {report.errors}"
    assert report.platform_detected == "workable"
    assert report.jobs_discovered >= 15
    assert report.jobs_accepted >= 15


def test_redsift_teamtailor_fixture_parsing():
    from src.app.scraper.platforms.teamtailor import TeamtailorAdapter
    from bs4 import BeautifulSoup

    html_path = FIXTURES_DIR / "redsift_careers.html"
    assert html_path.exists(), "Red Sift HTML fixture must exist"
    html_text = html_path.read_text(encoding="utf-8")

    # 1. Test DOM-based extraction
    soup = BeautifulSoup(html_text, "html.parser")
    dom_jobs = TeamtailorAdapter.parse_html(soup, "https://careers.redsift.com/jobs")
    assert len(dom_jobs) == 5, f"Expected 5 jobs from DOM, got {len(dom_jobs)}"
    dom_titles = {j.title for j in dom_jobs}
    assert "Sales Development Representative (SDR)" in dom_titles
    assert "IAM Product Engineer" in dom_titles
    assert "Business Automation Manager" in dom_titles

    # 2. Test RSS XML extraction
    rss_path = FIXTURES_DIR / "redsift_jobs.rss"
    assert rss_path.exists(), "Red Sift RSS fixture must exist"
    rss_text = rss_path.read_text(encoding="utf-8")
    rss_jobs = TeamtailorAdapter.parse_rss(rss_text, "https://careers.redsift.com/jobs")
    assert len(rss_jobs) == 5, f"Expected 5 jobs from RSS, got {len(rss_jobs)}"
    for job in rss_jobs:
        assert job.title
        assert "careers.redsift.com/jobs/" in job.job_url
        assert job.description and len(job.description) > 50

    # 3. Test Universal Strategy parsing on Red Sift source
    source = make_source("https://careers.redsift.com/jobs", html_text, "text/html; charset=utf-8")
    strategy = UniversalScraperStrategy()
    result = strategy.parse(source)
    assert len(result.jobs) == 5, f"Expected 5 jobs from UniversalScraperStrategy, got {len(result.jobs)}"


def test_live_redsift_discovery():
    report = run_scraper_diagnostics("https://careers.redsift.com/jobs", max_pages=1)
    assert report.status in ("SUCCESS", "PARTIAL_SUCCESS"), f"Expected success, got {report.status} with errors {report.errors}"
    assert report.jobs_discovered == 5, f"Expected 5 jobs, discovered {report.jobs_discovered}"
    assert report.jobs_accepted == 5
    assert report.jobs_rejected == 0
    titles = [j["title"] for j in report.sample_jobs]
    assert "Sales Development Representative (SDR)" in titles
    assert "IAM Product Engineer" in titles
    assert "Business Automation Manager" in titles
