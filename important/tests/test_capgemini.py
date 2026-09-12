import json
from pathlib import Path
from datetime import datetime, timezone

from src.app.scraper.capgemini_parser import (
    find_capgemini_next_page_url,
    parse_capgemini_jobs,
    resolve_capgemini_fetch_url,
)
from src.app.scraper.http_client import FetchedSource
from src.app.scraper.registry import CapgeminiScraperStrategy

FIXTURE_JSON = Path(__file__).parent / "fixtures" / "capgemini_api_response.json"


def test_resolve_capgemini_fetch_url() -> None:
    portal_url = "https://www.capgemini.com/ma-en/job-search?page=1&size=11&country_code=ma-en"
    api_url = resolve_capgemini_fetch_url(portal_url)
    assert "https://cg-jobstream-api.azurewebsites.net/api/job-search" in api_url
    assert "country_code=ma-en" in api_url
    assert "size=11" in api_url
    assert "page=1" in api_url


def test_parse_capgemini_jobs() -> None:
    source = FetchedSource(
        requested_url="https://cg-jobstream-api.azurewebsites.net/api/job-search?page=1&size=11&country_code=ma-en",
        final_url="https://cg-jobstream-api.azurewebsites.net/api/job-search?page=1&size=11&country_code=ma-en",
        status_code=200,
        content_type="application/json",
        body=FIXTURE_JSON.read_text(encoding="utf-8"),
        fetched_at=datetime.now(timezone.utc),
    )

    result = parse_capgemini_jobs(source)
    assert result.errors == []
    assert len(result.jobs) == 11

    first = result.jobs[0]
    assert first.external_job_id in ("548232-en_US", "548232-en_US_SAPBTP")
    assert "Responsable Qualit" in first.title
    assert first.location == "Casablanca"
    assert first.employment_type in ("Permanent", "full_time")
    assert first.posted_at is not None
    assert "https://careers.capgemini.com/job/" in first.job_url


def test_find_capgemini_next_page_url() -> None:
    source = FetchedSource(
        requested_url="https://cg-jobstream-api.azurewebsites.net/api/job-search?page=1&size=11&country_code=ma-en",
        final_url="https://cg-jobstream-api.azurewebsites.net/api/job-search?page=1&size=11&country_code=ma-en",
        status_code=200,
        content_type="application/json",
        body=FIXTURE_JSON.read_text(encoding="utf-8"),
        fetched_at=datetime.now(timezone.utc),
    )

    next_url = find_capgemini_next_page_url(source)
    assert next_url is not None
    assert "page=2" in next_url


def test_capgemini_strategy_can_handle() -> None:
    strategy = CapgeminiScraperStrategy()
    target = type("Target", (), {"url": "https://www.capgemini.com/ma-en/job-search", "type": "careers"})()
    company = type("Company", (), {"name": "Capgemini"})()
    assert strategy.can_handle(target, company) is True
