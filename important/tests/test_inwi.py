from datetime import datetime, timezone
from pathlib import Path

from src.app.scraper.http_client import FetchedSource
from src.app.scraper.inwi_parser import find_inwi_next_page_url, parse_inwi_jobs
from src.app.scraper.registry import InwiScraperStrategy

FIXTURE_PAGE_1 = Path(__file__).parent / "fixtures" / "inwi_page_1.html"
FIXTURE_PAGE_2 = Path(__file__).parent / "fixtures" / "inwi_page_2.html"


def test_parse_inwi_jobs_page_1() -> None:
    source = FetchedSource(
        requested_url="https://jobs.inwi.ma/jobs/",
        final_url="https://jobs.inwi.ma/jobs/",
        status_code=200,
        content_type="text/html",
        body=FIXTURE_PAGE_1.read_text(encoding="utf-8"),
        fetched_at=datetime.now(timezone.utc),
    )

    result = parse_inwi_jobs(source)
    assert result.errors == []
    assert len(result.jobs) == 20

    first = result.jobs[0]
    assert first.external_job_id == "8333225"
    assert "Analyste Senior" in first.title
    assert "https://jobs.inwi.ma/jobs/8333225" in first.job_url
    assert first.department is not None


def test_find_inwi_next_page_url() -> None:
    source = FetchedSource(
        requested_url="https://jobs.inwi.ma/jobs/",
        final_url="https://jobs.inwi.ma/jobs/",
        status_code=200,
        content_type="text/html",
        body=FIXTURE_PAGE_1.read_text(encoding="utf-8"),
        fetched_at=datetime.now(timezone.utc),
    )

    next_url = find_inwi_next_page_url(source)
    assert next_url is not None
    assert "/jobs/show_more?page=2" in next_url


def test_parse_inwi_turbo_stream_page_2() -> None:
    source = FetchedSource(
        requested_url="https://jobs.inwi.ma/jobs/show_more?page=2",
        final_url="https://jobs.inwi.ma/jobs/show_more?page=2",
        status_code=200,
        content_type="text/vnd.turbo-stream.html",
        body=FIXTURE_PAGE_2.read_text(encoding="utf-8"),
        fetched_at=datetime.now(timezone.utc),
    )

    result = parse_inwi_jobs(source)
    assert len(result.jobs) > 0


def test_inwi_strategy_can_handle() -> None:
    strategy = InwiScraperStrategy()
    target = type("Target", (), {"url": "https://jobs.inwi.ma/jobs/", "type": "careers"})()
    company = type("Company", (), {"name": "Inwi"})()
    assert strategy.can_handle(target, company) is True
