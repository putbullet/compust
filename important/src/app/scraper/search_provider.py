import re
import time
from abc import ABC, abstractmethod
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from ..logging import get_logger
from .url_normalizer import normalize_url

logger = get_logger("scraper.search_provider")


class SearchProvider(ABC):
    """Abstract provider for web search discovery of internship candidate pages."""

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[str]:
        """Perform search and return list of candidate URLs."""
        pass


class MockSearchProvider(SearchProvider):
    """Deterministic mock provider for automated tests and fixture pipelines."""

    def __init__(self, predefined_results: dict[str, list[str]] | None = None) -> None:
        self.predefined_results = predefined_results or {}
        self.default_urls: list[str] = []
        self.recorded_queries: list[str] = []

    def set_default_results(self, urls: list[str]) -> None:
        self.default_urls = urls

    def add_result(self, query: str, urls: list[str]) -> None:
        self.predefined_results[query.lower().strip()] = urls

    def search(self, query: str, limit: int = 10) -> list[str]:
        self.recorded_queries.append(query)
        q_norm = query.lower().strip()
        for key, urls in self.predefined_results.items():
            if key in q_norm or q_norm in key:
                return urls[:limit]
        return self.default_urls[:limit]


class DuckDuckGoHtmlSearchProvider(SearchProvider):
    """Public web discovery using public search engine results.

    Does NOT bypass bot protections, CAPTCHAs, or WAFs.
    Applies rate-limiting, timeouts, and graceful degradation on 403/429.
    """

    def __init__(self, timeout_seconds: float = 10.0, delay_seconds: float = 1.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.delay_seconds = delay_seconds
        self._last_request_time: float = 0.0

    def _rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self._last_request_time = time.time()

    def search(self, query: str, limit: int = 10) -> list[str]:
        self._rate_limit()
        urls: list[str] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        search_url = "https://html.duckduckgo.com/html/"
        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
                resp = client.post(search_url, data={"q": query}, headers=headers)
                if resp.status_code in (403, 429):
                    logger.warning(
                        f"Search provider rate-limited or access denied: HTTP {resp.status_code}",
                        extra={"event": "SEARCH_ACCESS_DENIED", "status_code": resp.status_code, "query": query},
                    )
                    return []
                if resp.status_code != 200:
                    logger.warning(f"Search provider HTTP {resp.status_code} for query: {query}")
                    return []

                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.select(".result__url, .result__snippet, .result__title a"):
                    href = a.get("href", "")
                    # DuckDuckGo HTML results redirect via /l/?uddg=<actual_url>
                    if "uddg=" in href:
                        parsed = urlparse(href)
                        qs = parse_qs(parsed.query)
                        actual_url = qs.get("uddg", [""])[0]
                        if actual_url:
                            actual_url = unquote(actual_url)
                            norm = normalize_url(actual_url)
                            if norm and norm.startswith("http") and norm not in urls:
                                urls.append(norm)
                    elif href.startswith("http"):
                        norm = normalize_url(href)
                        if norm and norm not in urls:
                            urls.append(norm)

                    if len(urls) >= limit:
                        break

        except Exception as exc:
            logger.warning(f"Search provider query failed gracefully: {exc}", extra={"event": "SEARCH_PROVIDER_ERROR", "query": query})
            return []

        return urls[:limit]
