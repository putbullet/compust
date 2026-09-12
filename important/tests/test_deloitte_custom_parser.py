from datetime import datetime, timezone
import pytest
from src.app.models import Company, ScrapeTarget
from src.app.scraper.custom.deloitte_parser import DeloitteScraperStrategy, parse_deloitte_jobs
from src.app.scraper.http_client import FetchedSource
from src.app.scraper.registry import get_strategy_for_target


def make_source(url: str, body: str) -> FetchedSource:
    return FetchedSource(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        body=body,
        fetched_at=datetime.now(timezone.utc),
    )


def test_deloitte_strategy_match():
    strategy = DeloitteScraperStrategy()
    t1 = ScrapeTarget(id=1, company_id=1, url="https://jobs.deloitte.com/search-jobs", active=True)
    c1 = Company(id=1, name="Deloitte", website_url="https://deloitte.com", careers_url="https://jobs.deloitte.com", active=True)
    assert strategy.can_handle(t1, c1) is True

    t2 = ScrapeTarget(id=2, company_id=2, url="https://careers.smartrecruiters.com/other", active=True)
    c2 = Company(id=2, name="Other", website_url="https://other.com", careers_url=None, active=True)
    assert strategy.can_handle(t2, c2) is False


def test_deloitte_parser_html_extraction():
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <section id="search-results-list">
            <ul>
                <li class="job-tile" data-job-id="456789">
                    <a href="/job/casablanca/consultant-cybersecurite/123/456789">
                        <h2>Consultant Senior Cybersécurité</h2>
                        <span class="job-location">Casablanca, Morocco</span>
                    </a>
                </li>
                <li class="card--job" data-job-id="987654">
                    <a href="https://jobs.deloitte.com/job/paris/audit-manager/123/987654">
                        <h2>Manager Audit Financier</h2>
                        <span class="job-location">Paris, France</span>
                    </a>
                </li>
            </ul>
        </section>
    </body>
    </html>
    """
    source = make_source("https://jobs.deloitte.com/search-jobs", html)
    result = parse_deloitte_jobs(source)

    assert len(result.errors) == 0
    assert len(result.jobs) == 2
    j1 = result.jobs[0]
    assert j1.title == "Consultant Senior Cybersécurité"
    assert "Casablanca" in (j1.location or "")
    assert j1.external_job_id == "456789"

    j2 = result.jobs[1]
    assert j2.title == "Manager Audit Financier"
    assert "Paris" in (j2.location or "")


def test_deloitte_registry_resolution():
    target = ScrapeTarget(id=99, company_id=99, url="https://jobs.deloitte.com/search-jobs", active=True)
    company = Company(id=99, name="Deloitte", website_url="https://deloitte.com", careers_url="https://jobs.deloitte.com", active=True)
    strat = get_strategy_for_target(target, company)
    assert strat.name == "deloitte"
