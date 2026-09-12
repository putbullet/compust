from datetime import datetime, timezone
import pytest
from src.app.scraper.http_client import FetchedSource
from src.app.scraper.universal_parser import (
    parse_universal_jobs,
    extract_json_ld_jobs,
    extract_html_card_jobs,
    is_plausible_job_link,
)


def make_source(url: str, body: str) -> FetchedSource:
    return FetchedSource(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        body=body,
        fetched_at=datetime.now(timezone.utc),
    )


def test_universal_parser_json_ld_single():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Careers at Acme</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Senior Backend Engineer",
            "description": "<p>We are seeking a Python and FastAPI specialist.</p>",
            "datePosted": "2026-03-01",
            "url": "https://acme.com/jobs/101",
            "employmentType": "FULL_TIME",
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Casablanca",
                    "addressCountry": "MA"
                }
            },
            "baseSalary": {
                "@type": "MonetaryAmount",
                "currency": "MAD",
                "value": {
                    "@type": "QuantitativeValue",
                    "minValue": 30000,
                    "maxValue": 45000,
                    "unitText": "MONTH"
                }
            }
        }
        </script>
    </head>
    <body><h1>Join Acme</h1></body>
    </html>
    """
    source = make_source("https://acme.com/careers", html)
    result = parse_universal_jobs(source)

    assert len(result.errors) == 0
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.title == "Senior Backend Engineer"
    assert job.job_url == "https://acme.com/jobs/101"
    assert "Casablanca" in (job.location or "")
    assert job.salary_min == 30000
    assert job.salary_max == 45000
    assert job.salary_currency == "MAD"


def test_universal_parser_json_ld_graph():
    html = """
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "JobPosting",
                    "title": "Data Scientist",
                    "url": "https://company.org/careers/ds-202",
                    "jobLocationType": "TELECOMMUTE"
                },
                {
                    "@type": "JobPosting",
                    "title": "Ingénieur DevOps",
                    "url": "/careers/devops-303"
                }
            ]
        }
        </script>
    </head>
    <body></body>
    </html>
    """
    source = make_source("https://company.org/careers", html)
    result = parse_universal_jobs(source)

    assert len(result.jobs) == 2
    assert result.jobs[0].title == "Data Scientist"
    assert result.jobs[0].remote_type == "remote"
    assert result.jobs[1].title == "Ingénieur DevOps"
    assert result.jobs[1].job_url == "https://company.org/careers/devops-303"


def test_universal_parser_html_card_heuristic():
    html = """
    <html>
    <body>
        <div class="career-listings">
            <div class="job-item card">
                <h3 class="job-title"><a href="/jobs/view/456">Cloud Infrastructure Architect</a></h3>
                <span class="location">Rabat, Morocco</span>
                <span class="department">Engineering</span>
                <span class="type">Full-time</span>
            </div>
            <div class="job-item card">
                <a class="job-link" href="https://other.com/jobs/789">Frontend React Developer</a>
                <p class="meta">Remote | Contract</p>
            </div>
        </div>
        <footer>
            <a href="/privacy">Privacy Policy</a>
            <a href="/about">About Us</a>
            <a href="/terms">Terms of Service</a>
        </footer>
    </body>
    </html>
    """
    source = make_source("https://company.com/careers", html)
    result = parse_universal_jobs(source)

    titles = [j.title for j in result.jobs]
    assert "Cloud Infrastructure Architect" in titles
    assert "Frontend React Developer" in titles
    # Ensure navigation links are strictly rejected
    assert "Privacy Policy" not in titles
    assert "About Us" not in titles
    assert "Terms of Service" not in titles


def test_universal_parser_rejects_empty_and_noise():
    html = """
    <html>
    <body>
        <nav>
            <a href="/contact">Contact Support</a>
            <a href="/login">Sign In</a>
            <a href="/careers">Careers</a>
            <a href="/blog">Our Blog</a>
        </nav>
    </body>
    </html>
    """
    source = make_source("https://noise.com/careers", html)
    result = parse_universal_jobs(source)
    assert len(result.jobs) == 0


def test_is_plausible_job_link_filters():
    assert is_plausible_job_link("/careers/jobs/123", "Lead Python Developer") is True
    assert is_plausible_job_link("/privacy", "Privacy Policy") is False
    assert is_plausible_job_link("/about-us", "About Our Company") is False
    assert is_plausible_job_link("/cookie-policy", "Cookies") is False
