import pytest
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from src.app.scraper.spa_detector import is_spa_shell
from src.app.scraper.http_client import FetchedSource, SourceFetchError
from src.app.scraper.crawler import crawl_pages, CrawlResult
from src.app.scraper.registry import UniversalScraperStrategy
from src.app.scraper.diagnostics import DiagnosticReport, run_scraper_diagnostics
from src.app.scraper.orange_parser import JobCandidate, ParseResult
from src.app.scraper.browser_fetch import is_playwright_available, fetch_rendered_source


def _make_source(body: str, url: str = "https://example.com/careers", is_rendered: bool = False) -> FetchedSource:
    return FetchedSource(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html; charset=utf-8",
        body=body,
        fetched_at=datetime.now(timezone.utc),
        is_rendered=is_rendered,
    )


# ---------------------------------------------------------------------------
# 1. SPA Detector Unit Tests
# ---------------------------------------------------------------------------

def test_spa_detector_empty_root_elements():
    html_root = "<html><head><title>App</title></head><body><div id='root'></div><script src='/bundle.js'></script></body></html>"
    assert is_spa_shell(html_root) is True

    html_app = "<html><body><div id='app'><noscript>You need JS</noscript></div></body></html>"
    assert is_spa_shell(html_app) is True

    html_next = "<html><body><div id='__next'></div></body></html>"
    assert is_spa_shell(html_next) is True


def test_spa_detector_noscript_js_required():
    html = """
    <html>
        <body>
            <noscript>You need to enable JavaScript to run this app.</noscript>
            <div>Welcome</div>
        </body>
    </html>
    """
    assert is_spa_shell(html) is True


def test_spa_detector_bundle_scripts_with_minimal_text():
    html = """
    <!DOCTYPE html>
    <html>
      <head><title>Career Portal</title></head>
      <body>
        <div id="wrapper"></div>
        <script src="/static/js/main.89a7cf.chunk.js"></script>
        <script src="/static/js/bundle.js"></script>
      </body>
    </html>
    """
    assert is_spa_shell(html) is True


def test_spa_detector_normal_static_page_returns_false():
    html = """
    <!DOCTYPE html>
    <html>
      <head><title>Our Company Careers</title></head>
      <body>
        <header><nav><a href="/">Home</a><a href="/careers">Careers</a></nav></header>
        <main>
          <h1>Join Our Growing Team</h1>
          <p>We are looking for passionate individuals to join us in building the future of cloud computing.</p>
          <div class="jobs-list">
            <article class="job-item">
              <h2>Senior Python Engineer</h2>
              <p>Location: Remote</p>
              <a href="/careers/senior-python-engineer">Apply Now</a>
            </article>
            <article class="job-item">
              <h2>Frontend React Developer</h2>
              <p>Location: Casablanca, Morocco</p>
              <a href="/careers/frontend-developer">Apply Now</a>
            </article>
          </div>
        </main>
        <footer><p>&copy; 2026 Example Corp.</p></footer>
      </body>
    </html>
    """
    assert is_spa_shell(html) is False


# ---------------------------------------------------------------------------
# 2. Crawler Browser Fallback Integration Tests (Mock Fetchers)
# ---------------------------------------------------------------------------

def test_crawler_browser_fallback_activates_on_spa():
    static_spa_html = """
    <!DOCTYPE html>
    <html>
      <head><title>TechCorp Careers</title></head>
      <body>
        <div id="root"></div>
        <script src="/app.bundle.js"></script>
      </body>
    </html>
    """
    hydrated_rendered_html = """
    <!DOCTYPE html>
    <html>
      <head><title>TechCorp Careers</title></head>
      <body>
        <div id="root">
          <section class="open-positions">
            <h2>Current Openings</h2>
            <div class="job-card">
              <a href="https://example.com/jobs/senior-software-engineer">Senior Software Engineer</a>
              <span>Remote / Full-time</span>
            </div>
            <div class="job-card">
              <a href="https://example.com/jobs/data-scientist">Data Scientist</a>
              <span>Casablanca, Morocco</span>
            </div>
          </section>
        </div>
      </body>
    </html>
    """

    strategy = UniversalScraperStrategy()
    url = "https://example.com/careers"

    fetch_call_count = 0
    rendered_call_count = 0

    def mock_fetcher(fetch_url, **kwargs):
        nonlocal fetch_call_count
        fetch_call_count += 1
        return _make_source(static_spa_html, url=fetch_url, is_rendered=False)

    def mock_rendered_fetcher(fetch_url, **kwargs):
        nonlocal rendered_call_count
        rendered_call_count += 1
        return _make_source(hydrated_rendered_html, url=fetch_url, is_rendered=True)

    crawl_res = crawl_pages(
        url,
        strategy,
        fetcher=mock_fetcher,
        rendered_fetcher=mock_rendered_fetcher,
        enable_browser_fallback=True,
    )

    # 1. Verify both fetchers were called in sequence
    assert fetch_call_count == 1
    assert rendered_call_count == 1

    # 2. Verify jobs were discovered from the rendered DOM
    assert len(crawl_res.jobs) >= 2
    titles = [j.title for j in crawl_res.jobs]
    assert any("Senior Software Engineer" in t for t in titles)
    assert any("Data Scientist" in t for t in titles)

    # 3. Verify initial_source is marked as rendered
    assert crawl_res.initial_source is not None
    assert crawl_res.initial_source.is_rendered is True

    # 4. Verify diagnostic trace contains the browser fallback notice
    assert any("[Browser Fallback] Hydrated client-rendered SPA shell via headless browser" in err for err in crawl_res.errors)


def test_crawler_browser_fallback_bypassed_when_static_succeeds():
    rich_static_html = """
    <!DOCTYPE html>
    <html>
      <body>
        <section>
          <h2>Careers</h2>
          <ul>
            <li><a href="https://example.com/job/devops">DevOps Engineer</a></li>
            <li><a href="https://example.com/job/qa">QA Automation Engineer</a></li>
          </ul>
        </section>
      </body>
    </html>
    """

    strategy = UniversalScraperStrategy()
    url = "https://example.com/careers"

    rendered_called = False

    def mock_fetcher(fetch_url, **kwargs):
        return _make_source(rich_static_html, url=fetch_url, is_rendered=False)

    def mock_rendered_fetcher(fetch_url, **kwargs):
        nonlocal rendered_called
        rendered_called = True
        return _make_source("", url=fetch_url, is_rendered=True)

    crawl_res = crawl_pages(
        url,
        strategy,
        fetcher=mock_fetcher,
        rendered_fetcher=mock_rendered_fetcher,
        enable_browser_fallback=True,
    )

    # Should find jobs statically and NEVER invoke rendered_fetcher
    assert len(crawl_res.jobs) == 2
    assert rendered_called is False
    assert crawl_res.initial_source.is_rendered is False


def test_crawler_browser_fallback_disabled_setting():
    static_spa_html = "<html><body><div id='root'></div></body></html>"
    strategy = UniversalScraperStrategy()
    url = "https://example.com/careers"

    rendered_called = False

    def mock_fetcher(fetch_url, **kwargs):
        return _make_source(static_spa_html, url=fetch_url, is_rendered=False)

    def mock_rendered_fetcher(fetch_url, **kwargs):
        nonlocal rendered_called
        rendered_called = True
        return _make_source("<html><body>Jobs</body></html>", url=fetch_url, is_rendered=True)

    crawl_res = crawl_pages(
        url,
        strategy,
        fetcher=mock_fetcher,
        rendered_fetcher=mock_rendered_fetcher,
        enable_browser_fallback=False,  # Explicitly disabled
    )

    assert len(crawl_res.jobs) == 0
    assert rendered_called is False


def test_crawler_browser_fallback_graceful_on_rendered_failure():
    static_spa_html = "<html><body><div id='root'></div></body></html>"
    strategy = UniversalScraperStrategy()
    url = "https://example.com/careers"

    def mock_fetcher(fetch_url, **kwargs):
        return _make_source(static_spa_html, url=fetch_url, is_rendered=False)

    def mock_failing_rendered_fetcher(fetch_url, **kwargs):
        raise SourceFetchError("Playwright browser rendering timed out after 15s")

    crawl_res = crawl_pages(
        url,
        strategy,
        fetcher=mock_fetcher,
        rendered_fetcher=mock_failing_rendered_fetcher,
        enable_browser_fallback=True,
    )

    # Must not crash, should report failure gracefully
    assert len(crawl_res.jobs) == 0
    assert any("[Browser Fallback] Headless browser rendering attempt failed" in err for err in crawl_res.errors)


def test_crawler_browser_fallback_recovers_403_challenge():
    hydrated_html = """
    <html>
      <body>
        <section>
          <h2>Open Roles</h2>
          <div><a href="https://example.com/job/sre">Site Reliability Engineer</a></div>
          <div><a href="https://example.com/job/ml">Machine Learning Engineer</a></div>
        </section>
      </body>
    </html>
    """
    strategy = UniversalScraperStrategy()
    url = "https://example.com/careers"

    def mock_fetcher(fetch_url, **kwargs):
        raise SourceFetchError("source restricted: Cloudflare WAF challenge detected. (https://example.com/careers)", status_code=403)

    def mock_rendered_fetcher(fetch_url, **kwargs):
        return _make_source(hydrated_html, url=fetch_url, is_rendered=True)

    crawl_res = crawl_pages(
        url,
        strategy,
        fetcher=mock_fetcher,
        rendered_fetcher=mock_rendered_fetcher,
        enable_browser_fallback=True,
    )

    assert len(crawl_res.jobs) >= 2
    assert crawl_res.initial_source.is_rendered is True
    assert any("[Browser Fallback] Recovered from restricted static fetch" in err for err in crawl_res.errors)


# ---------------------------------------------------------------------------
# 3. Live Playwright Headless Rendering Test
# ---------------------------------------------------------------------------

def test_playwright_live_local_html_hydration():
    """
    Spins up Playwright against an inline client-rendered data URL
    and verifies that JavaScript renders the DOM and the Universal
    parser with Job Title Intelligence discovers the jobs.
    """
    if not is_playwright_available():
        pytest.skip("Playwright is not available in the test environment")

    spa_page_html = """
    <!DOCTYPE html>
    <html>
      <head><title>SPA Live Test</title></head>
      <body>
        <div id="root">Loading careers...</div>
        <script>
          setTimeout(() => {
            const root = document.getElementById('root');
            root.innerHTML = `
              <div class="career-section">
                <h2>Explore Careers</h2>
                <ul>
                  <li><a href="https://example.com/jobs/cloud-architect">Cloud Architect</a></li>
                  <li><a href="https://example.com/jobs/security-engineer">Security Engineer</a></li>
                </ul>
              </div>
            `;
          }, 150);
        </script>
      </body>
    </html>
    """
    import base64
    b64_content = base64.b64encode(spa_page_html.encode("utf-8")).decode("utf-8")
    data_url = f"data:text/html;base64,{b64_content}"

    # Fetch rendered source via Playwright
    rendered_source = fetch_rendered_source(data_url, timeout_seconds=10.0)

    assert rendered_source.is_rendered is True
    assert "Cloud Architect" in rendered_source.body
    assert "Security Engineer" in rendered_source.body

    # Run universal parser on the hydrated DOM
    strategy = UniversalScraperStrategy()
    result = strategy.parse(rendered_source)

    assert len(result.jobs) >= 2
    titles = [j.title for j in result.jobs]
    assert "Cloud Architect" in titles
    assert "Security Engineer" in titles


def test_diagnostics_report_browser_rendered(monkeypatch):
    """Verify run_scraper_diagnostics marks browser_rendered=True when fallback runs."""
    static_spa_html = "<html><body><div id='root'></div></body></html>"
    hydrated_rendered_html = """
    <html>
      <body>
        <section>
          <h2>Open Positions</h2>
          <div><a href="https://example.com/jobs/backend-engineer">Backend Engineer</a></div>
          <div><a href="https://example.com/jobs/frontend-engineer">Frontend Engineer</a></div>
        </section>
      </body>
    </html>
    """

    url = "https://example.com/careers"

    # Monkeypatch fetch_source and fetch_rendered_source in diagnostics's module namespace
    monkeypatch.setattr(
        "src.app.scraper.crawler.fetch_source",
        lambda fetch_url, **kwargs: _make_source(static_spa_html, url=fetch_url, is_rendered=False)
    )
    monkeypatch.setattr(
        "src.app.scraper.crawler.fetch_rendered_source",
        lambda fetch_url, **kwargs: _make_source(hydrated_rendered_html, url=fetch_url, is_rendered=True)
    )

    report = run_scraper_diagnostics(url)

    assert report.browser_rendered is True
    assert report.rendering_mode == "spa_client_rendered"
    assert report.jobs_accepted >= 2
    assert report.discovery_method is not None
    assert "browser_rendered" in report.discovery_method

