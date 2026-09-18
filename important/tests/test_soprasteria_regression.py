from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import pytest

from src.app.scraper.crawler import crawl_pages
from src.app.scraper.http_client import FetchedSource
from src.app.scraper.registry import UniversalScraperStrategy
from src.app.scraper.spa_detector import is_spa_shell
from src.app.scraper.universal_parser import find_universal_next_page_url

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def make_source(url: str, body: str) -> FetchedSource:
    return FetchedSource(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html; charset=utf-8",
        body=body,
        fetched_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sopra_page_1_html() -> str:
    path = FIXTURES_DIR / "soprasteria_filtered.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def sopra_page_2_html() -> str:
    path = FIXTURES_DIR / "soprasteria_page_2.html"
    return path.read_text(encoding="utf-8")


def test_spa_detector_no_str_parent_crash(sopra_page_1_html):
    """
    Regression test: is_spa_shell must safely inspect body text without raising
    "'str' object has no attribute 'parent'".
    """
    # This call must execute smoothly without exception
    is_spa = is_spa_shell(sopra_page_1_html)
    assert isinstance(is_spa, bool)
    assert not is_spa


def test_soprasteria_page_1_parsing(sopra_page_1_html):
    """
    Verify universal HTML parser extracts 6 jobs from page 1 of Sopra Steria,
    preserves French accents, extracts valid locations, classifies stages/internships,
    rejects CTA button text as titles, and detects 9 total results.
    """
    base_url = "https://careers.soprasteria.fr/jobs?options=209%2C218&page=1"
    source = make_source(base_url, sopra_page_1_html)
    strategy = UniversalScraperStrategy()
    result = strategy.parse(source)

    assert result.detected_result_count == 9
    assert len(result.jobs) == 6

    for job in result.jobs:
        # Title must not be empty or generic CTA button
        assert job.title
        assert "VOIR L'OFFRE" not in job.title.upper()
        assert "POSTULER" not in job.title.upper()
        assert "VIEW JOB" not in job.title.upper()

        # Job URL must be absolute and point to Sopra Steria careers
        assert job.job_url.startswith("https://careers.soprasteria.fr/job/") or job.job_url.startswith("https://careers.soprasteria.fr/jobs/")

        # Location should be captured
        assert job.location is not None and len(job.location) > 0

    # Verify French accents are preserved in title text
    all_titles_text = " ".join(j.title for j in result.jobs)
    has_accent = any(ord(c) > 127 for c in all_titles_text)
    assert has_accent, f"Expected accented characters in titles, got: {all_titles_text}"

    # Verify at least one internship/stage title is correctly classified
    # Sopra Steria filtered page includes stages (e.g. Stage Développeur(se) Big Data / Ingénieur(e) Cybersécurité)
    stage_jobs = [j for j in result.jobs if "stage" in j.title.lower()]
    assert len(stage_jobs) >= 1
    for sj in stage_jobs:
        assert sj.employment_type == "internship"


def test_soprasteria_pagination_discovery(sopra_page_1_html, sopra_page_2_html):
    """
    Verify pagination logic finds page 2 from page 1, and does not loop on page 2.
    """
    base_url_1 = "https://careers.soprasteria.fr/jobs?options=209%2C218&page=1"
    next_url = find_universal_next_page_url(sopra_page_1_html, base_url_1)

    assert next_url is not None
    assert "page=2" in next_url

    base_url_2 = "https://careers.soprasteria.fr/jobs?options=209%2C218&page=2"
    next_url_2 = find_universal_next_page_url(sopra_page_2_html, base_url_2)
    # Page 2 is the last page (9 results total: 6 on page 1, 3 on page 2)
    assert next_url_2 is None or "page=2" not in next_url_2


def test_soprasteria_end_to_end_crawl_simulation(sopra_page_1_html, sopra_page_2_html):
    """
    Simulate full multi-page crawl across both pages and verify all 9 jobs are extracted
    with 0 errors and detected_result_count == 9.
    """
    url_1 = "https://careers.soprasteria.fr/jobs?options=209%2C218&page=1"
    url_2 = "https://careers.soprasteria.fr/jobs?options=209%2C218&page=2"

    from datetime import datetime, timezone

    def mock_fetch(url, *args, **kwargs):
        now = datetime.now(timezone.utc)
        if "page=2" in url:
            return FetchedSource(requested_url=url, final_url=url, body=sopra_page_2_html, status_code=200, content_type="text/html", fetched_at=now)
        return FetchedSource(requested_url=url, final_url=url, body=sopra_page_1_html, status_code=200, content_type="text/html", fetched_at=now)

    strategy = UniversalScraperStrategy()

    with patch("src.app.scraper.crawler.fetch_source", side_effect=mock_fetch):
        crawl_res = crawl_pages(url_1, strategy, max_pages=3)

    assert len(crawl_res.errors) == 0
    assert len(crawl_res.jobs) == 9
    assert crawl_res.detected_result_count == 9
    assert crawl_res.pages_crawled == 2

    # Check that URLs are unique across the 9 jobs
    job_urls = [j.job_url for j in crawl_res.jobs]
    assert len(set(job_urls)) == 9
