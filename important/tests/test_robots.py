from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, Country, ScrapeTarget
from src.app.scraper.http_client import FetchedSource, SourceFetchError
from src.app.scraper.robots_checker import (
    is_path_allowed_by_robots,
    verify_target_robots_compliance,
)


def test_is_path_allowed_by_robots(monkeypatch) -> None:
    robots_body = """
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /careers/
"""
    monkeypatch.setattr(
        "src.app.scraper.robots_checker.fetch_source",
        lambda url: FetchedSource(
            requested_url=url,
            final_url=url,
            status_code=200,
            content_type="text/plain",
            body=robots_body,
            fetched_at=datetime.now(timezone.utc),
        ),
    )

    assert is_path_allowed_by_robots("https://example.test/careers/search") is True
    assert is_path_allowed_by_robots("https://example.test/admin/dashboard") is False
    assert is_path_allowed_by_robots("https://example.test/private/data") is False


def test_robots_txt_404_allows_all(monkeypatch) -> None:
    def raise_404(url):
        raise SourceFetchError("Not found", 404)

    monkeypatch.setattr("src.app.scraper.robots_checker.fetch_source", raise_404)
    assert is_path_allowed_by_robots("https://example.test/careers") is True


def test_verify_target_sets_source_disallowed(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        country = Country(name="Morocco", code="MA")
        company = Company(name="DisallowedCo", website_url="https://blocked.test", active=True, countries=[country])
        session.add(company)
        session.flush()
        target = ScrapeTarget(
            company_id=company.id,
            url="https://blocked.test/blocked-careers",
            type="careers",
            active=True,
            status=None,
        )
        session.add(target)
        session.commit()
        target_id = target.id

        monkeypatch.setattr("src.app.scraper.robots_checker.is_path_allowed_by_robots", lambda url, **kw: False)

        allowed = verify_target_robots_compliance(session, target)
        assert allowed is False
        assert target.status == "SOURCE_DISALLOWED"
        assert target.robots_txt_allowed is False
        assert target.robots_txt_checked_at is not None

        # Verify API blocks requests with 403
        def fake_db():
            with session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = fake_db
        client = TestClient(app)
        res = client.post(f"/api/v1/scrape-targets/{target_id}/inspect")
        app.dependency_overrides.clear()

        assert res.status_code == 403
        assert "SOURCE_DISALLOWED" in res.json()["detail"]
    engine.dispose()
