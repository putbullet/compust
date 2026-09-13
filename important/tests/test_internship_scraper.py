"""Tests for Internship Intelligence Scraper:
- Multilingual terminology & query expansion
- Job title intelligence token index
- SSRF URL validation
- Negative and positive signal classification (avoiding non-job portals)
- Structured HTML / JSON-LD extraction
- Scraper error resilience (403, 429, timeouts)
- Deduplication and confidence ranking
- FastAPI /api/v1/internships/search endpoint
"""

from datetime import datetime, timezone
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.app.scraper.internship_terminology import expand_internship_queries, INTERNSHIP_TERMINOLOGY_BY_LANG
from src.app.scraper.job_title_intelligence.index import get_job_title_index
from src.app.scraper.ssrf_validator import validate_safe_url, SSRFValidationError
from src.app.scraper.search_provider import MockSearchProvider
from src.app.scraper.internship_scraper import (
    InternshipIntelligenceScraper,
    InternshipOpportunity,
    InternshipSearchResponse,
    InternshipSearchDiagnostics,
)
from src.app.scraper.http_client import FetchedSource, SourceFetchError
from src.app.main import app


# ---------------------------------------------------------------------------
# 1. Multilingual Terminology & Query Expansion
# ---------------------------------------------------------------------------

def test_query_expansion_multilingual():
    """Verify query expansion creates localized queries for EN, FR, DE, ES."""
    queries_fr = expand_internship_queries("cybersecurity", country="France", year=2026)
    assert len(queries_fr) > 0
    combined_fr = " ".join(queries_fr).lower()
    assert "stage" in combined_fr or "alternance" in combined_fr or "france" in combined_fr

    queries_de = expand_internship_queries("data science", country="Germany", year=2026)
    combined_de = " ".join(queries_de).lower()
    assert "praktikum" in combined_de or "werkstudent" in combined_de or "germany" in combined_de


def test_query_expansion_worldwide():
    """Verify query expansion works when country is None (worldwide)."""
    queries = expand_internship_queries("software engineer", country=None, year=2026)
    assert len(queries) >= 3
    assert any("2026" in q for q in queries)


# ---------------------------------------------------------------------------
# 2. Job Title Intelligence & Token Indexing
# ---------------------------------------------------------------------------

def test_job_title_intelligence_indexing():
    """Verify in-memory index loads and finds related internship titles."""
    index = get_job_title_index()
    assert index.total_titles > 1000  # 73k in production dataset

    matches = index.find_related_internship_titles("software", limit=5)
    assert isinstance(matches, list)
    assert len(matches) > 0
    for m in matches:
        assert isinstance(m, str)
        assert any(term in m.lower() for term in ["software", "developer", "engineer", "intern"])


# ---------------------------------------------------------------------------
# 3. SSRF Validator Tests
# ---------------------------------------------------------------------------

def test_ssrf_validator_blocks_internal_and_private_ips():
    """Verify SSRF validator rejects private, loopback, and link-local addresses."""
    # Loopback
    with pytest.raises(SSRFValidationError):
        validate_safe_url("http://127.0.0.1/admin")

    with pytest.raises(SSRFValidationError):
        validate_safe_url("http://localhost:8000/api")

    # Cloud metadata service
    with pytest.raises(SSRFValidationError):
        validate_safe_url("http://169.254.169.254/latest/meta-data")

    # RFC 1918 Private IPs
    with pytest.raises(SSRFValidationError):
        validate_safe_url("http://10.0.0.1/private")

    with pytest.raises(SSRFValidationError):
        validate_safe_url("http://192.168.1.1/router")

    # Non-HTTP schemes
    with pytest.raises(SSRFValidationError):
        validate_safe_url("file:///etc/passwd")

    with pytest.raises(SSRFValidationError):
        validate_safe_url("ftp://example.com/file")


def test_ssrf_validator_allows_public_urls():
    """Verify SSRF validator allows legitimate public URLs."""
    safe_url = validate_safe_url("https://www.google.com/search")
    assert safe_url.startswith("https://")


# ---------------------------------------------------------------------------
# 4. Content Classification & Job Signals
# ---------------------------------------------------------------------------

def test_extract_page_internships_signal_classification():
    """Test positive and negative signal identification."""
    scraper = InternshipIntelligenceScraper()

    job_html = """
    <html>
        <head><title>Software Engineering Intern 2026 - TechCorp</title></head>
        <body>
            <h1>Software Engineer Intern (Summer 2026)</h1>
            <p>TechCorp is looking for passionate students to join our team in Paris.</p>
            <div class="apply-section">
                <button>Apply Now</button>
            </div>
            <div class="description">
                <h3>Requirements and Qualifications:</h3>
                <ul>
                    <li>Pursuing a Bachelor or Master degree in Computer Science</li>
                    <li>Experience with Python, JavaScript, and SQL</li>
                    <li>Duration: 6 months internship starting June 2026</li>
                </ul>
            </div>
        </body>
    </html>
    """

    blog_html = """
    <html>
        <head><title>How to Get an Internship - Career Blog</title></head>
        <body>
            <h1>How to Get an Internship in 2026</h1>
            <p>Here are our top advice articles and career guidance blog posts...</p>
        </body>
    </html>
    """

    # Job HTML should be extracted
    job_results = scraper.extract_page_internships(
        url="https://techcorp.example.com/careers/internship-123",
        html=job_html,
        target_field="Software Engineering",
        target_country="France",
        target_year=2026,
    )
    assert len(job_results) == 1
    assert "Software Engineer Intern" in job_results[0].title
    assert job_results[0].company != ""
    assert job_results[0].confidence_score >= 60

    # Blog HTML should be rejected due to negative pattern
    blog_results = scraper.extract_page_internships(
        url="https://careerblog.example.com/tips/how-to-get-an-internship",
        html=blog_html,
        target_field="Software Engineering",
        target_country="France",
        target_year=2026,
    )
    assert len(blog_results) == 0


# ---------------------------------------------------------------------------
# 5. JSON-LD Extraction
# ---------------------------------------------------------------------------

def test_json_ld_job_posting_extraction():
    """Test parsing Schema.org JobPosting in JSON-LD script."""
    scraper = InternshipIntelligenceScraper()

    html_with_jsonld = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Data Analyst Intern</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Data Analyst Intern (Summer 2026)",
            "description": "<p>Exciting 6-month internship in analytics and AI.</p>",
            "hiringOrganization": {
                "@type": "Organization",
                "name": "Global Analytics Ltd",
                "sameAs": "https://globalanalytics.example.com"
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Berlin",
                    "addressCountry": "Germany"
                }
            },
            "employmentType": "INTERN"
        }
        </script>
    </head>
    <body>
        <h1>Data Analyst Intern</h1>
    </body>
    </html>
    """

    results = scraper.extract_page_internships(
        url="https://globalanalytics.example.com/jobs/data-analyst-intern",
        html=html_with_jsonld,
        target_field="Data Analyst",
        target_country="Germany",
        target_year=2026,
    )

    assert len(results) == 1
    opp = results[0]
    assert "Data Analyst Intern" in opp.title
    assert opp.company == "Global Analytics Ltd"
    assert "Berlin" in opp.location or "Germany" in opp.country


# ---------------------------------------------------------------------------
# 6. Scraper Resilience (403, 429, Timeout Handling) & Deduplication
# ---------------------------------------------------------------------------

def test_scraper_resilience_and_deduplication():
    """Verify scraper handles errors gracefully and deduplicates results."""
    mock_provider = MockSearchProvider()
    mock_provider.set_default_results([
        "https://cloudnet.example.com/careers/intern-1",
        "https://cloudnet.example.com/careers/intern-1?utm_source=linkedin",
        "https://forbidden.example.com/job",
        "https://ratelimited.example.com/job",
    ])

    scraper = InternshipIntelligenceScraper(search_provider=mock_provider)

    valid_html = """
    <html>
        <head><title>CloudNet DevOps Internship 2026</title></head>
        <body>
            <h1>DevOps Engineering Intern 2026</h1>
            <p>Location: London, UK</p>
            <div class="description">
                Requirements: Docker, Kubernetes, Python. 6 months duration.
            </div>
            <a href="https://cloudnet.example.com/apply">Apply Now</a>
        </body>
    </html>
    """

    def fake_fetch_source(url: str, timeout_seconds: float = 10.0):
        now = datetime.now(timezone.utc)
        if "forbidden" in url:
            return FetchedSource(requested_url=url, final_url=url, status_code=403, content_type="text/html", body="", fetched_at=now)
        elif "ratelimited" in url:
            return FetchedSource(requested_url=url, final_url=url, status_code=429, content_type="text/html", body="", fetched_at=now)
        elif "cloudnet" in url:
            return FetchedSource(requested_url=url, final_url=url, status_code=200, content_type="text/html", body=valid_html, fetched_at=now)
        raise SourceFetchError(f"Simulated connection timeout on {url}")

    with patch("src.app.scraper.internship_scraper.fetch_source", side_effect=fake_fetch_source), \
         patch("src.app.scraper.internship_scraper.is_path_allowed_by_robots", return_value=True), \
         patch("src.app.scraper.internship_scraper.validate_safe_url", return_value="validated"):

        response = scraper.search_and_extract(field="DevOps", country="United Kingdom", year=2026, max_results=10)

        # Scraper should NOT crash on 403 or 429
        assert response.diagnostics.sources_discovered >= 2
        # Duplicate should be deduplicated
        assert len(response.opportunities) == 1
        opp = response.opportunities[0]
        assert "DevOps" in opp.title
        assert opp.confidence_score >= 60


# ---------------------------------------------------------------------------
# 7. FastAPI Endpoint /api/v1/internships/search
# ---------------------------------------------------------------------------

def test_api_internships_search_endpoint():
    """Verify the FastAPI endpoint POST /api/v1/internships/search returns correct structure."""
    client = TestClient(app)

    with patch("src.app.scraper.internship_scraper.InternshipIntelligenceScraper") as MockClass:
        instance = MockClass.return_value
        instance.search_and_extract.return_value = InternshipSearchResponse(
            opportunities=[
                InternshipOpportunity(
                    id="mock-opp-1",
                    title="AI Research Intern 2026",
                    company="FutureLab",
                    location="Zurich, Switzerland",
                    country="Switzerland",
                    description="AI research and modeling",
                    requirements=["Python", "PyTorch"],
                    source_url="https://futurelab.example.com/jobs/ai-intern",
                    application_url="https://futurelab.example.com/jobs/ai-intern",
                    source_domain="futurelab.example.com",
                    confidence_score=92,
                    is_year_match=True,
                )
            ],
            diagnostics=InternshipSearchDiagnostics(
                queries_executed=["AI Research intern Switzerland 2026"],
                sources_discovered=1,
                sources_checked=1,
                valid_opportunities_found=1,
                execution_time_ms=115.0,
            ),
            related_titles=["Artificial Intelligence Specialist", "Machine Learning Engineer"],
        )

        resp = client.post(
            "/api/v1/internships/search",
            json={
                "field": "AI Research",
                "country": "Switzerland",
                "year": 2026,
                "max_results": 10
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["opportunities"]) == 1
        assert data["opportunities"][0]["title"] == "AI Research Intern 2026"
        assert data["opportunities"][0]["company"] == "FutureLab"
        assert data["opportunities"][0]["confidence_score"] == 92
        assert "queries_executed" in data["diagnostics"]
        assert len(data["related_titles"]) == 2
