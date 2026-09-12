import time
from datetime import datetime, timezone
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

from src.app.scraper.http_client import FetchedSource
from src.app.scraper.job_title_intelligence import (
    JobTitleIndex,
    JobTitleMatcher,
    OpportunityClusterDetector,
    OpportunityScorer,
    discover_jobs_via_title_intelligence,
    get_job_title_index,
    normalize_title,
    strip_title_noise,
    generate_normalized_variants,
)
from src.app.scraper.registry import UniversalScraperStrategy
from src.app.scraper.universal_parser import parse_universal_jobs
from src.app.scraper.diagnostics import run_scraper_diagnostics

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


# --------------------------------------------------------------------------
# TEST 1: A normal page containing no jobs. Expected: No job discovery.
# --------------------------------------------------------------------------
def test_case_01_normal_page_no_jobs():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>About Our Bakery</title></head>
    <body>
        <h1>Fresh Artisanal Bread Every Morning</h1>
        <p>We bake sourdough, baguettes, and croissants using traditional French techniques.</p>
        <div>
            <h2>Our History</h2>
            <p>Founded in 1998, we have been serving the local community with quality flour and water.</p>
        </div>
        <footer><p>&copy; 2026 French Bakery Inc.</p></footer>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs, diag = discover_jobs_via_title_intelligence(soup, "https://bakery.example.com")
    assert len(jobs) == 0
    assert diag["candidates_count"] == 0

    source = make_source("https://bakery.example.com", html)
    res = parse_universal_jobs(source)
    assert len(res.jobs) == 0


# --------------------------------------------------------------------------
# TEST 2: A page containing one generic word "Engineer" in an unrelated article.
# Expected: No job discovery.
# --------------------------------------------------------------------------
def test_case_02_single_generic_word_in_article():
    html = """
    <html>
    <head><title>Tech Blog - Infrastructure Migration</title></head>
    <body>
        <article class="blog-post">
            <h1>How We Scaled Our Distributed Cache</h1>
            <p class="author">Written by John Doe, an engineer on our platform team.</p>
            <p>When our traffic grew by 500%, every engineer worked around the clock to migrate from Redis to Valkey.</p>
            <p>Our lead developer noted that memory consumption dropped significantly.</p>
        </article>
        <div class="comments">
            <p>Great post! Thanks for sharing the architectural insights.</p>
        </div>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs, diag = discover_jobs_via_title_intelligence(soup, "https://blog.example.com/scale")
    assert len(jobs) == 0, f"Expected 0 jobs, found {len(jobs)}"

    source = make_source("https://blog.example.com/scale", html)
    res = parse_universal_jobs(source)
    assert len(res.jobs) == 0


# --------------------------------------------------------------------------
# TEST 3: A page containing several recognizable job titles inside one section.
# Expected: Section detected.
# --------------------------------------------------------------------------
def test_case_03_several_job_titles_inside_one_section():
    html = """
    <html>
    <body>
        <div class="company-overview">
            <h1>Acme Global Innovations</h1>
            <p>We build enterprise cloud solutions for multinational banks.</p>
        </div>
        <div class="services">
            <h2>Our Services</h2>
            <p>Consulting, Cloud Migration, Auditing.</p>
        </div>
        <section class="openings-container">
            <h2>Join Our Growing Engineering Team</h2>
            <div class="role-entry">
                <h3>Senior Backend Engineer</h3>
                <p>Build scalable microservices in Go and Python.</p>
            </div>
            <div class="role-entry">
                <h3>Frontend Developer</h3>
                <p>Craft responsive UI in React and TypeScript.</p>
            </div>
            <div class="role-entry">
                <h3>Cybersecurity Analyst</h3>
                <p>Monitor SIEM alerts and conduct penetration testing.</p>
            </div>
        </section>
        <div class="contact">
            <h2>Contact Us</h2>
            <p>Email: contact@acme.example.com</p>
        </div>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs, diag = discover_jobs_via_title_intelligence(soup, "https://acme.example.com/about")
    assert len(jobs) >= 3, f"Expected at least 3 jobs, found {len(jobs)}"
    assert diag["best_cluster_tag"] == "section"
    titles = [j.title for j in jobs]
    assert any("Senior Backend Engineer" in t for t in titles)
    assert any("Frontend Developer" in t for t in titles)
    assert any("Cybersecurity Analyst" in t for t in titles)


# --------------------------------------------------------------------------
# TEST 4: Several job titles with clickable URLs.
# Expected: Correct candidate URLs discovered.
# --------------------------------------------------------------------------
def test_case_04_job_titles_with_clickable_urls():
    html = """
    <html>
    <body>
        <section class="team-roles-wrapper">
            <h2>Current Opportunities</h2>
            <div class="role-entry">
                <a href="/team-roles/101-senior-backend-engineer">Senior Backend Engineer</a>
                <span class="location">Casablanca, Morocco</span>
            </div>
            <div class="role-entry">
                <a href="/team-roles/102-frontend-developer">Frontend Developer</a>
                <span class="location">Remote</span>
            </div>
            <div class="role-entry">
                <a href="/team-roles/103-machine-learning-engineer">Machine Learning Engineer</a>
                <span class="location">Paris, France</span>
            </div>
        </section>
    </body>
    </html>
    """
    source = make_source("https://techcorp.ma/careers", html)
    res = parse_universal_jobs(source)
    assert len(res.jobs) == 3
    urls = {j.job_url for j in res.jobs}
    assert "https://techcorp.ma/team-roles/101-senior-backend-engineer" in urls
    assert "https://techcorp.ma/team-roles/102-frontend-developer" in urls
    assert "https://techcorp.ma/team-roles/103-machine-learning-engineer" in urls

    locations = {j.location for j in res.jobs}
    assert "Casablanca, Morocco" in locations
    assert "Remote" in locations


# --------------------------------------------------------------------------
# TEST 5: Job titles spread across unrelated sections.
# Expected: No false merging.
# --------------------------------------------------------------------------
def test_case_05_titles_spread_across_unrelated_sections_no_merging():
    html = """
    <html>
    <body>
        <section class="about-team">
            <h2>Our Leadership</h2>
            <div class="bio">
                <h4>Alice Smith</h4>
                <p>Director of Operations with 20 years in logistics.</p>
            </div>
        </section>
        <section class="case-study">
            <h2>Client Success</h2>
            <p>Our Senior Software Engineer collaborated with customer engineers on migration.</p>
        </section>
        <section class="news">
            <h2>Company News</h2>
            <p>We welcome our new Chief Financial Officer.</p>
        </section>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs, diag = discover_jobs_via_title_intelligence(soup, "https://example.com/company")
    assert len(jobs) == 0, f"Expected 0 jobs due to disparate unrelated sections, got {len(jobs)}"


# --------------------------------------------------------------------------
# TEST 6: Several job titles inside a repeated card/list structure.
# Expected: High-confidence opportunity region.
# --------------------------------------------------------------------------
def test_case_06_repeated_card_list_structure():
    html = """
    <html>
    <body>
        <div class="portal-body">
            <div class="vacancies-block">
                <h2>Open Vacancies</h2>
                <ul class="positions-list">
                    <li class="vacancy-card">
                        <a href="/jobs/devops">DevOps Engineer</a>
                        <span class="type">Full-Time</span>
                        <span class="location">Rabat</span>
                    </li>
                    <li class="vacancy-card">
                        <a href="/jobs/cloud-sec">Cloud Security Engineer</a>
                        <span class="type">CDI</span>
                        <span class="location">Casablanca</span>
                    </li>
                    <li class="vacancy-card">
                        <a href="/jobs/data-eng">Data Engineer</a>
                        <span class="type">Hybrid</span>
                        <span class="location">Casablanca</span>
                    </li>
                    <li class="vacancy-card">
                        <a href="/jobs/qa-lead">QA Automation Engineer</a>
                        <span class="type">Full-Time</span>
                        <span class="location">Remote</span>
                    </li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs, diag = discover_jobs_via_title_intelligence(soup, "https://cloudfirm.ma/portal")
    assert len(jobs) >= 4
    assert diag["best_cluster_confidence"] >= 0.75, f"Expected >= 0.75, got {diag['best_cluster_confidence']}"


# --------------------------------------------------------------------------
# TEST 7: Titles with capitalization/whitespace/punctuation variations.
# Expected: Correct normalized matching.
# --------------------------------------------------------------------------
def test_case_07_normalization_variations():
    # Test normalization function directly
    assert normalize_title("Senior   Software   Engineer") == "senior software engineer"
    assert normalize_title("Senior\nSoftware\tEngineer") == "senior software engineer"
    assert normalize_title("Senior Software-Engineer") == "senior software engineer"
    assert normalize_title("Frontend Developer (m/f/d)") == "front end developer"
    assert normalize_title("BACKEND ENGINEER - FULL TIME") == "back end engineer"

    # Test through HTML discovery
    html = """
    <html>
    <body>
        <section class="careers">
            <h2>Current Openings</h2>
            <div class="card"><a href="/job/1">SENIOR  SOFTWARE   ENGINEER (M/F/D)</a></div>
            <div class="card"><a href="/job/2">Front-End  Developer (Remote)</a></div>
            <div class="card"><a href="/job/3">Cybersecurity&#39;s Operations Analyst</a></div>
        </section>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs, diag = discover_jobs_via_title_intelligence(soup, "https://normalized.example.com")
    assert len(jobs) >= 2, f"Expected >= 2 jobs, got {len(jobs)}"
    titles = [j.title.lower() for j in jobs]
    assert any("senior software engineer" in t for t in titles)


# --------------------------------------------------------------------------
# TEST 8: Duplicate titles.
# Expected: Correct deduplication of title matches.
# --------------------------------------------------------------------------
def test_case_08_duplicate_titles_deduplicated():
    html = """
    <html>
    <body>
        <section class="job-list">
            <h2>Open Positions</h2>
            <div class="item"><a href="/roles/backend-1">Senior Backend Engineer</a></div>
            <div class="item"><a href="/roles/backend-1">Senior Backend Engineer</a></div>
            <div class="item"><a href="/roles/backend-2">Senior Backend Engineer</a></div>
            <div class="item"><a href="/roles/frontend-1">Frontend Developer</a></div>
        </section>
    </body>
    </html>
    """
    source = make_source("https://dedup.example.com/careers", html)
    res = parse_universal_jobs(source)
    # The duplicate URL /roles/backend-1 should be deduplicated
    urls = [j.job_url for j in res.jobs]
    assert len(urls) == len(set(urls)), f"Found duplicate URLs: {urls}"


# --------------------------------------------------------------------------
# TEST 9: Same title appearing in navigation and actual job section.
# Expected: Actual job section wins based on context.
# --------------------------------------------------------------------------
def test_case_09_navigation_vs_actual_section():
    html = """
    <html>
    <body>
        <nav class="main-navigation">
            <a href="/home">Home</a>
            <a href="/services">Services</a>
            <a href="/roles/engineer">Software Engineer</a>
            <a href="/contact">Contact</a>
        </nav>
        <main>
            <div class="hero"><h1>Welcome to FinTech Solutions</h1></div>
            <section class="careers-openings">
                <h2>Work With Us</h2>
                <div class="card"><a href="/careers/swe">Software Engineer</a></div>
                <div class="card"><a href="/careers/devops">DevOps Engineer</a></div>
                <div class="card"><a href="/careers/product">Product Manager</a></div>
            </section>
        </main>
        <footer><p>FinTech Solutions Ltd.</p></footer>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs, diag = discover_jobs_via_title_intelligence(soup, "https://fintech.example.com")
    assert len(jobs) >= 3
    # The links should be from the career section, NOT the navigation link
    job_urls = [j.job_url for j in jobs]
    assert "https://fintech.example.com/careers/swe" in job_urls
    assert "https://fintech.example.com/roles/engineer" not in job_urls


# --------------------------------------------------------------------------
# TEST 10: Job title with no link but valid job-card context.
# Expected: Candidate region retained without inventing URL.
# --------------------------------------------------------------------------
def test_case_10_job_title_no_link_retained_with_slug_anchor():
    html = """
    <html>
    <body>
        <section class="current-openings">
            <h2>Positions Available</h2>
            <div class="job-card">
                <h3>Cloud Infrastructure Architect</h3>
                <p>Full-time &bull; Casablanca &bull; Python, Terraform, AWS</p>
                <p>Send your CV directly to hr@moroccotech.ma quoting reference CIA-2026.</p>
            </div>
            <div class="job-card">
                <h3>Cybersecurity Operations Analyst</h3>
                <p>CDI &bull; Remote &bull; SIEM, SOC, Splunk</p>
                <p>Send your CV directly to hr@moroccotech.ma quoting reference COA-2026.</p>
            </div>
        </section>
    </body>
    </html>
    """
    source = make_source("https://moroccotech.ma/careers", html)
    res = parse_universal_jobs(source)
    assert len(res.jobs) >= 2, f"Expected at least 2 jobs, got {len(res.jobs)}"
    for job in res.jobs:
        # Check that external URL was not invented, but preserved with clean anchor
        assert job.job_url.startswith("https://moroccotech.ma/careers#")
        assert len(job.job_url.split("#")[1]) >= 3
        assert job.external_job_id


# --------------------------------------------------------------------------
# TEST 11: 70K-title dataset loading/indexing performance.
# Expected: Loads successfully and within reasonable time.
# --------------------------------------------------------------------------
def test_case_11_dataset_loading_performance():
    index = get_job_title_index()
    stats = index.stats()
    assert stats["total_titles"] >= 70000, f"Expected >= 70000 titles, got {stats['total_titles']}"
    assert stats["unique_titles"] >= 70000
    assert stats["first_word_keys"] >= 5000
    # Verified in-memory lookup is sub-millisecond
    t0 = time.perf_counter()
    for _ in range(100):
        index.is_known_title("senior backend engineer")
        index.is_known_title("cybersecurity analyst")
        index.is_known_title("unrelated non job string here")
    lookup_duration = (time.perf_counter() - t0) * 1000
    assert lookup_duration < 10.0, f"300 lookups took {lookup_duration:.2f}ms, expected < 10ms"


# --------------------------------------------------------------------------
# TEST 12: Existing successful scraper fixture regression.
# Expected: No regression on Rankly Media.
# --------------------------------------------------------------------------
def test_case_12_existing_fixture_no_regression():
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
    assert expected_titles.issubset(titles)


# --------------------------------------------------------------------------
# TEST 13: Existing parser receives candidates generated by the new layer.
# Expected: Correct normalized job output with skills and locations.
# --------------------------------------------------------------------------
def test_case_13_candidates_flow_through_normalization():
    html = """
    <html>
    <body>
        <section class="recruitment-section">
            <h2>Career Opportunities</h2>
            <div class="custom-position-entry">
                <a href="/opportunites/python-dev">Python Backend Engineer</a>
                <span class="location">Casablanca</span>
                <p>Requirements: Python, FastAPI, Docker, PostgreSQL.</p>
            </div>
            <div class="custom-position-entry">
                <a href="/opportunites/react-dev">Frontend Developer</a>
                <span class="location">Rabat</span>
                <p>Requirements: React, TypeScript, TailwindCSS.</p>
            </div>
        </section>
    </body>
    </html>
    """
    source = make_source("https://startup.ma/jobs", html)
    res = parse_universal_jobs(source)
    assert len(res.jobs) == 2
    for job in res.jobs:
        assert job.title
        assert job.job_url
        assert job.external_job_id
        assert job.discovery_source == "job_title_intelligence"
    
    python_job = next(j for j in res.jobs if "Python" in j.title)
    assert python_job.location == "Casablanca"
    assert "Python" in python_job.skills
    assert "FastAPI" in python_job.skills
    assert "Docker" in python_job.skills


# --------------------------------------------------------------------------
# TEST 14: A page where normal discovery already finds jobs (e.g. JSON-LD).
# Expected: Fallback is not unnecessarily invoked or destructive.
# --------------------------------------------------------------------------
def test_case_14_normal_discovery_preempts_fallback():
    html = """
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Principal Architect",
            "url": "https://enterprise.com/jobs/1"
        }
        </script>
    </head>
    <body>
        <section class="other-openings">
            <h2>Other Positions</h2>
            <div class="item"><a href="/jobs/2">Senior Cloud Engineer</a></div>
            <div class="item"><a href="/jobs/3">Site Reliability Engineer</a></div>
        </section>
    </body>
    </html>
    """
    source = make_source("https://enterprise.com/careers", html)
    res = parse_universal_jobs(source)
    # JSON-LD takes precedence in universal parser (Layer 3)
    assert len(res.jobs) == 1
    assert res.jobs[0].title == "Principal Architect"
    assert res.jobs[0].job_url == "https://enterprise.com/jobs/1"
    assert res.jobs[0].discovery_source is None  # standard JSON-LD candidate
