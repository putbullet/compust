from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, Job, JobSkill, ScrapeTarget, ScrapingRun
from src.app.scraper.cooldown import apply_target_outcome, is_in_cooldown
from src.app.scraper.registry import get_strategy_for_target
from src.app.scraper.run_service import finish_scraping_run, list_scraping_runs, start_scraping_run

PAGE_1 = Path(__file__).parent / "fixtures" / "orange_page_1.html"
PAGE_2 = Path(__file__).parent / "fixtures" / "orange_page_2.html"


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_cooldown_policy_and_expiry(db_session) -> None:
    company = Company(name="Orange Maroc", website_url="https://orange.ma", careers_url="https://orange.jobs", active=True)
    db_session.add(company)
    db_session.flush()

    target = ScrapeTarget(company_id=company.id, url="https://orange.jobs/fr/fr/search-results", type="orange", active=True)
    db_session.add(target)
    db_session.commit()

    in_cool, _ = is_in_cooldown(target)
    assert in_cool is False

    # 429 rate limit sets cooldown
    apply_target_outcome(db_session, target, "rate_limited")
    assert target.status == "rate_limited"
    assert target.cooldown_until is not None
    in_cool, msg = is_in_cooldown(target)
    assert in_cool is True
    assert "in cooldown" in msg

    # Success clears cooldown
    apply_target_outcome(db_session, target, "success")
    assert target.status == "success"
    assert target.cooldown_until is None
    in_cool, _ = is_in_cooldown(target)
    assert in_cool is False


def test_scraping_run_lifecycle(db_session) -> None:
    company = Company(name="Test Co", website_url="https://test.co", careers_url=None, active=True)
    db_session.add(company)
    db_session.flush()
    target = ScrapeTarget(company_id=company.id, url="https://test.co/jobs", type="orange", active=True)
    db_session.add(target)
    db_session.commit()

    run = start_scraping_run(db_session, company.id)
    assert run.status == "running"
    assert run.started_at is not None
    assert run.finished_at is None

    finish_scraping_run(
        db_session,
        run,
        jobs_found=5,
        jobs_added=3,
        jobs_updated=2,
        parser_errors=[],
    )
    assert run.status == "success"
    assert run.finished_at is not None
    assert run.jobs_found == 5
    assert run.jobs_added == 3

    runs = list_scraping_runs(db_session, company.id)
    assert len(runs) == 1
    assert runs[0].id == run.id


def test_strategy_resolver_not_bound_to_company_id_1() -> None:
    # Company with ID other than 1
    target = ScrapeTarget(id=99, company_id=55, url="https://orange.jobs/careers", type="orange", active=True)
    company = Company(id=55, name="Any Company", website_url="https://any.com", careers_url=None, active=True)
    strategy = get_strategy_for_target(target, company)
    assert strategy is not None
    assert strategy.name == "orange"


def test_api_enforces_cooldown_and_tracks_runs(db_session, monkeypatch) -> None:
    country = Country(name="Morocco", code="MA")
    company = Company(name="Orange Maroc", website_url="https://orange.ma", careers_url="https://orange.jobs", active=True)
    company.countries.append(country)
    db_session.add_all([country, company])
    db_session.flush()

    target = ScrapeTarget(company_id=company.id, url="https://orange.jobs/fr/fr/search-results", type="orange", active=True)
    db_session.add(target)
    db_session.commit()

    # Mock fetch_source in main to return page_1 content
    def mock_fetch(url, *args, **kwargs):
        return httpx.Response(200, text=PAGE_1.read_text(encoding="utf-8"), request=httpx.Request("GET", url))

    # Override httpx get in fetch_source
    monkeypatch.setattr(
        "src.app.scraper.crawler.fetch_source",
        lambda url, **kw: type("Source", (), {
            "requested_url": url,
            "final_url": url,
            "status_code": 200,
            "content_type": "text/html",
            "body": PAGE_2.read_text(encoding="utf-8") if "from=2" in url else PAGE_1.read_text(encoding="utf-8"),
            "fetched_at": datetime.now(timezone.utc),
        })()
    )

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        # 1. Sync target
        response = client.post(f"/api/v1/scrape-targets/{target.id}/sync?max_pages=2")
        assert response.status_code == 200
        data = response.json()
        assert data["jobs_found"] == 3
        assert data["jobs_added"] == 3

        # 2. Check runs endpoint
        runs_resp = client.get(f"/api/v1/scrape-targets/{target.id}/runs")
        assert runs_resp.status_code == 200
        runs_data = runs_resp.json()
        assert len(runs_data) == 1
        assert runs_data[0]["status"] == "success"
        assert runs_data[0]["jobs_found"] == 3

        # 3. Set cooldown manually on target and verify API returns 429
        apply_target_outcome(db_session, target, "rate_limited")
        blocked_resp = client.post(f"/api/v1/scrape-targets/{target.id}/sync")
        assert blocked_resp.status_code == 429
        assert "in cooldown" in blocked_resp.json()["detail"]

        blocked_parse = client.post(f"/api/v1/scrape-targets/{target.id}/parse")
        assert blocked_parse.status_code == 429
    finally:
        app.dependency_overrides.clear()
