from pathlib import Path
import httpx
import pytest

from src.app.scraper.crawler import crawl_pages
from src.app.scraper.http_client import FetchedSource, fetch_source
from src.app.scraper.orange_parser import find_orange_next_page_url, parse_orange_jobs
from src.app.scraper.registry import OrangeScraperStrategy

PAGE_1 = Path(__file__).parent / "fixtures" / "orange_page_1.html"
PAGE_2 = Path(__file__).parent / "fixtures" / "orange_page_2.html"


def test_find_orange_next_page_url() -> None:
    source1 = fetch_source(
        "https://orange.jobs/fr/fr/search-results",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    content=PAGE_1.read_bytes(),
                    request=request,
                )
            )
        ),
    )
    next_url = find_orange_next_page_url(source1)
    assert next_url == "https://orange.jobs/fr/fr/search-results?from=2&s=1"

    source2 = fetch_source(
        "https://orange.jobs/fr/fr/search-results?from=2&s=1",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    content=PAGE_2.read_bytes(),
                    request=request,
                )
            )
        ),
    )
    assert find_orange_next_page_url(source2) is None


def test_crawl_multi_page_discovers_all_jobs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "from=2" in url_str:
            return httpx.Response(200, headers={"content-type": "text/html"}, content=PAGE_2.read_bytes(), request=request)
        return httpx.Response(200, headers={"content-type": "text/html"}, content=PAGE_1.read_bytes(), request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    strategy = OrangeScraperStrategy()

    result = crawl_pages(
        "https://orange.jobs/fr/fr/search-results",
        strategy=strategy,
        max_pages=5,
        client=client,
    )

    assert result.pages_crawled == 2
    assert len(result.jobs) == 3
    job_ids = [job.external_job_id for job in result.jobs]
    assert job_ids == ["ORANGE-101", "ORANGE-102", "ORANGE-103"]
    # Verify tracking parameters were stripped from apply URLs
    assert result.jobs[0].job_url == "https://orange.jobs/fr/fr/job/101/apply"
    assert result.jobs[1].job_url == "https://orange.jobs/fr/fr/job/102/apply"


def test_crawl_terminates_on_repeated_job_ids() -> None:
    # Page always returns same content (page 1) with next link
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=PAGE_1.read_bytes(), request=request)
        )
    )
    strategy = OrangeScraperStrategy()

    result = crawl_pages(
        "https://orange.jobs/fr/fr/search-results",
        strategy=strategy,
        max_pages=10,
        client=client,
    )

    # Page 1 visited, then next URL requested returning the same jobs -> stopped after 2 requests
    assert result.pages_crawled == 2
    assert len(result.jobs) == 2


def test_crawl_respects_safety_max_pages_limit() -> None:
    page_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal page_count
        page_count += 1
        # Return page with unique jobId each time
        body = f"""
        <html><body>
          <a rel="next" href="/search?page={page_count+1}">Next</a>
          <script>
            var phApp = {{}};
            phApp.ddo = {{"eagerLoadRefineSearch":{{"status":200,"data":{{"jobs":[
              {{"jobId":"JOB-{page_count}","title":"Job {page_count}","applyUrl":"/job/{page_count}"}}
            ]}}}}}};
          </script>
        </body></html>
        """
        return httpx.Response(200, headers={"content-type": "text/html"}, content=body.encode("utf-8"), request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    strategy = OrangeScraperStrategy()

    result = crawl_pages(
        "https://example.com/search",
        strategy=strategy,
        max_pages=3,
        client=client,
    )

    assert result.pages_crawled == 3
    assert len(result.jobs) == 3
