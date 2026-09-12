import time
from dataclasses import dataclass
from typing import Callable

import httpx

from ..config import get_settings
from .http_client import FetchedSource, fetch_source
from .orange_parser import JobCandidate, ParseResult
from .registry import ScraperStrategy
from .url_normalizer import normalize_url


@dataclass(frozen=True)
class CrawlResult:
    jobs: list[JobCandidate]
    errors: list[str]
    pages_crawled: int
    initial_source: FetchedSource | None = None


def crawl_pages(
    entry_url: str,
    strategy: ScraperStrategy,
    *,
    max_pages: int | None = None,
    delay_seconds: float | None = None,
    client: httpx.Client | None = None,
    fetcher: Callable[..., FetchedSource] | None = None,
) -> CrawlResult:
    """
    Crawls pages following pagination discovery:
    - Stops on no next link
    - Stops on exhausted results (0 jobs parsed)
    - Stops on repeated job IDs (all candidate IDs already seen)
    - Stops when configured safety limit (max_pages) is reached
    - Normalizes URLs and prevents visited URL cycles
    - Respects configurable polite inter-request delay
    """
    settings = get_settings()
    page_limit = max_pages if max_pages is not None else settings.scraper_max_pages_limit
    # Only apply real delay if a custom mock fetcher is not injected (i.e. live crawling)
    request_delay = delay_seconds if delay_seconds is not None else (
        0.0 if fetcher is not None else settings.scraper_request_delay_seconds
    )

    current_url: str | None = normalize_url(entry_url)
    visited_urls: set[str] = set()
    seen_job_ids: set[str] = set()
    all_jobs: list[JobCandidate] = []
    all_errors: list[str] = []
    pages_crawled = 0
    initial_source: FetchedSource | None = None
    actual_fetcher = fetcher or fetch_source

    while current_url and pages_crawled < page_limit:
        if current_url in visited_urls:
            break
        visited_urls.add(current_url)

        fetch_url = current_url
        if hasattr(strategy, "resolve_fetch_url"):
            fetch_url = strategy.resolve_fetch_url(current_url)

        source = actual_fetcher(fetch_url, client=client)
        if initial_source is None:
            initial_source = source
        pages_crawled += 1

        result: ParseResult = strategy.parse(source)
        all_errors.extend(result.errors)

        if not result.jobs:
            # Exhausted results
            break

        # Check for repeated job IDs loop
        page_ids = {j.external_job_id for j in result.jobs if j.external_job_id}
        if page_ids and page_ids.issubset(seen_job_ids):
            # All job IDs on this page were already seen
            break

        for job in result.jobs:
            if not job.external_job_id or job.external_job_id not in seen_job_ids:
                if job.external_job_id:
                    seen_job_ids.add(job.external_job_id)
                all_jobs.append(job)

        next_url = strategy.find_next_page_url(source)
        if not next_url:
            break

        next_url = normalize_url(next_url)
        if next_url in visited_urls:
            break

        if request_delay > 0:
            time.sleep(request_delay)

        current_url = next_url

    return CrawlResult(jobs=all_jobs, errors=all_errors, pages_crawled=pages_crawled, initial_source=initial_source)
