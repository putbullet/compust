import logging
import time
from dataclasses import dataclass
from typing import Callable

import httpx

from ..config import get_settings
from .browser_fetch import fetch_rendered_source
from .http_client import FetchedSource, SourceFetchError, fetch_source
from .orange_parser import JobCandidate, ParseResult
from .registry import ScraperStrategy
from .spa_detector import is_spa_shell
from .url_normalizer import normalize_url

logger = logging.getLogger(__name__)


def count_html_job_signals(html: str) -> int:
    """Heuristically count job-like card or listing elements in raw HTML."""
    if not html:
        return 0
    import re
    data_jk = len(re.findall(r'data-jk=["\'][^"\']+["\']', html, re.IGNORECASE))
    if data_jk > 0:
        return data_jk
    data_job = len(re.findall(r'data-job[-_]?(?:id|key)?=["\'][^"\']+["\']', html, re.IGNORECASE))
    if data_job > 0:
        return data_job
    job_cards = len(re.findall(
        r'class=["\'][^"\']*\b(?:job[-_]?card|job[-_]?item|job[-_]?listing|vacancy[-_]?card|opening[-_]?card|result[-_]?card|posting[-_]?item)\b[^"\']*["\']',
        html,
        re.IGNORECASE,
    ))
    if job_cards > 0:
        return job_cards
    title_matches = len(re.findall(r'class=["\'][^"\']*\b(?:job[-_]?title|posting[-_]?title)\b[^"\']*["\']', html, re.IGNORECASE))
    if title_matches > 0:
        return title_matches
    return 0


@dataclass(frozen=True)
class CrawlResult:
    jobs: list[JobCandidate]
    errors: list[str]
    pages_crawled: int
    initial_source: FetchedSource | None = None
    detected_result_count: int | None = None
    stop_reason: str = "completed"
    content_signal_count: int = 0


def crawl_pages(
    entry_url: str,
    strategy: ScraperStrategy,
    *,
    max_pages: int | None = None,
    delay_seconds: float | None = None,
    client: httpx.Client | None = None,
    fetcher: Callable[..., FetchedSource] | None = None,
    rendered_fetcher: Callable[..., FetchedSource] | None = None,
    enable_browser_fallback: bool | None = None,
) -> CrawlResult:
    """
    Crawls pages following pagination discovery:
    - Stops on no next link
    - Stops on exhausted results (0 jobs parsed)
    - Stops on repeated job IDs (all candidate IDs already seen)
    - Stops when configured safety limit (max_pages) is reached
    - Normalizes URLs and prevents visited URL cycles
    - Respects configurable polite inter-request delay
    - Falls back to headless browser rendering for SPA shells yielding 0 static jobs
    """
    settings = get_settings()
    page_limit = max_pages if max_pages is not None else settings.scraper_max_pages_limit
    # Only apply real delay if a custom mock fetcher is not injected (i.e. live crawling)
    request_delay = delay_seconds if delay_seconds is not None else (
        0.0 if fetcher is not None else settings.scraper_request_delay_seconds
    )
    browser_fallback_active = (
        enable_browser_fallback
        if enable_browser_fallback is not None
        else settings.scraper_enable_browser_fallback
    )

    current_url: str | None = normalize_url(entry_url)
    visited_urls: set[str] = set()
    seen_job_ids: set[str] = set()
    all_jobs: list[JobCandidate] = []
    all_errors: list[str] = []
    pages_crawled = 0
    initial_source: FetchedSource | None = None
    detected_result_count: int | None = None
    actual_fetcher = fetcher or fetch_source
    actual_rendered_fetcher = rendered_fetcher or fetch_rendered_source
    stop_reason = "completed"
    content_signal_count = 0

    while current_url and pages_crawled < page_limit:
        if current_url in visited_urls:
            stop_reason = "completed"
            break
        visited_urls.add(current_url)

        fetch_url = current_url
        if hasattr(strategy, "resolve_fetch_url"):
            fetch_url = strategy.resolve_fetch_url(current_url)

        source: FetchedSource | None = None
        try:
            source = actual_fetcher(fetch_url, client=client)
        except SourceFetchError as exc:
            # Check if browser fallback can salvage a 403 or Cloudflare challenge
            if browser_fallback_active and any(k in str(exc).lower() for k in ("403", "cloudflare", "javascript")):
                try:
                    source = actual_rendered_fetcher(fetch_url)
                    all_errors.append(f"[Browser Fallback] Recovered from restricted static fetch via headless browser: {exc}")
                except Exception as b_exc:
                    all_errors.append(str(exc))
                    all_errors.append(f"[Browser Fallback] Headless browser recovery attempt failed: {b_exc}")
                    stop_reason = "error"
                    break
            else:
                all_errors.append(str(exc))
                stop_reason = "rate_limited" if "429" in str(exc) else "error"
                break

        if source is None:
            stop_reason = "error"
            break

        if initial_source is None:
            initial_source = source
        pages_crawled += 1
        content_signal_count += count_html_job_signals(source.body)

        result: ParseResult = strategy.parse(source)

        # Headless Browser Rendering Fallback for SPA shells with 0 discovered jobs
        if not result.jobs and browser_fallback_active and not source.is_rendered:
            is_spa = is_spa_shell(source.body)
            has_spa_error = any("Client-rendered SPA shell" in err for err in result.errors)
            is_universal = getattr(strategy, "name", "") == "universal"

            if is_spa or has_spa_error or is_universal:
                try:
                    rendered_source = actual_rendered_fetcher(fetch_url)
                    if rendered_source and rendered_source.body:
                        rendered_result = strategy.parse(rendered_source)
                        if rendered_result.jobs:
                            source = rendered_source
                            if pages_crawled == 1:
                                initial_source = rendered_source
                            result = rendered_result
                            content_signal_count += count_html_job_signals(rendered_source.body)
                            all_errors.append(
                                f"[Browser Fallback] Hydrated client-rendered SPA shell via headless browser; discovered {len(rendered_result.jobs)} job candidate(s)."
                            )
                        else:
                            all_errors.append("[Browser Fallback] Rendered page via headless browser, but 0 qualifying jobs were found in hydrated DOM.")
                except Exception as b_exc:
                    all_errors.append(f"[Browser Fallback] Headless browser rendering attempt failed: {b_exc}")

        all_errors.extend(result.errors)

        if not result.jobs:
            # Exhausted results
            stop_reason = "no_new_jobs"
            break

        # Check for repeated job IDs loop
        page_ids = {j.external_job_id for j in result.jobs if j.external_job_id}
        if page_ids and page_ids.issubset(seen_job_ids):
            # All job IDs on this page were already seen
            stop_reason = "no_new_jobs"
            break

        if result.detected_result_count is not None and detected_result_count is None:
            detected_result_count = result.detected_result_count

        for job in result.jobs:
            if not job.external_job_id or job.external_job_id not in seen_job_ids:
                if job.external_job_id:
                    seen_job_ids.add(job.external_job_id)
                all_jobs.append(job)

        next_url = strategy.find_next_page_url(source)
        if not next_url:
            stop_reason = "completed"
            break

        next_url = normalize_url(next_url)
        if next_url in visited_urls:
            stop_reason = "completed"
            break

        if pages_crawled >= page_limit:
            stop_reason = "max_pages_reached"
            break

        if request_delay > 0:
            time.sleep(request_delay)

        current_url = next_url

    if pages_crawled >= page_limit and stop_reason == "completed":
        stop_reason = "max_pages_reached"

    return CrawlResult(
        jobs=all_jobs,
        errors=all_errors,
        pages_crawled=pages_crawled,
        initial_source=initial_source,
        detected_result_count=detected_result_count,
        stop_reason=stop_reason,
        content_signal_count=content_signal_count,
    )

