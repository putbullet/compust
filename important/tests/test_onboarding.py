from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app
from src.app.models import Base, Company, ScrapeTarget
from src.app.schemas_onboarding import CompanyOnboardRequest
from src.app.scraper.classifier import classify_portal
from src.app.services.onboarding_service import onboard_company_and_target


def test_classify_portal_heuristics() -> None:
    # 1. Workday heuristic
    wd_html = '<div data-automation-id="workday-wd3-search">Careers</div>'
    wd_res = classify_portal("https://company.myworkdayjobs.com/en-US/careers", html=wd_html)
    assert wd_res.portal_type == "workday"
    assert wd_res.pagination_style == "offset_limit"

    # 2. SmartRecruiters heuristic
    sr_html = '<div class="smartrecruiters-job-list">Jobs</div>'
    sr_res = classify_portal("https://careers.smartrecruiters.com/AcmeCorp", html=sr_html)
    assert sr_res.portal_type == "smartrecruiters"
    assert "smartrecruiters" in sr_res.recommendation.lower()

    # 3. Turbo-stream heuristic
    ts_html = '<turbo-frame id="jobs"><a href="/jobs?page=2" class="show_more">More</a></turbo-frame>'
    ts_res = classify_portal("https://recrutement.example.ma/postes", html=ts_html)
    assert ts_res.portal_type == "turbostream_html"
    assert ts_res.pagination_style == "show_more_button"

    # 4. Standard HTML rel="next"
    rel_html = '<link rel="next" href="/jobs?page=2"><div class="job-item">Dev</div>'
    rel_res = classify_portal("https://careers.telecom.ma/search", html=rel_html)
    assert rel_res.portal_type == "server_rendered_html"
    assert rel_res.pagination_style == "rel_next"


def test_onboarding_service_and_api() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def fake_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    # Test via API
    resp = client.post(
        "/api/v1/admin/onboard",
        json={
            "name": "Attijariwafa Bank",
            "website_url": "https://www.attijariwafabank.com",
            "careers_url": "https://carrieres.attijariwafabank.com/offres",
            "country_code": "MA",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["company_name"] == "Attijariwafa Bank"
    assert data["country_code"] == "MA"
    assert data["scrape_target_id"] > 0
    assert "classification" in data
    assert data["classification"]["portal_type"] in ["server_rendered_html", "unknown"]

    # Verify DB state
    with session_factory() as db:
        target = db.get(ScrapeTarget, data["scrape_target_id"])
        assert target is not None
        assert target.company_id == data["company_id"]
        assert target.active is True
        assert target.url == "https://carrieres.attijariwafabank.com/offres"

    app.dependency_overrides.clear()
    engine.dispose()
