from dataclasses import dataclass
from datetime import datetime, timezone
import random

import httpx


class SourceFetchError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class FetchedSource:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    body: str
    fetched_at: datetime


from ..config import get_settings

# Realistic browser-grade User-Agent strings for fallback on 403
_BROWSER_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]

# Full browser-grade request headers sent alongside a real UA
_BROWSER_HEADERS: dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


def _is_cloudflare_challenge(response: httpx.Response) -> bool:
    """Detect Cloudflare / WAF JavaScript challenge pages."""
    server = response.headers.get("server", "").lower()
    if "cloudflare" in server:
        return True
    body_lower = response.text[:1000].lower()
    cf_signals = [
        "just a moment",
        "enable javascript and cookies",
        "challenges.cloudflare.com",
        "__cf_bm",
        "cf-ray",
        "ray id",
        "checking your browser",
        "ddos protection by cloudflare",
    ]
    return any(sig in body_lower for sig in cf_signals)


def fetch_source(
    url: str,
    *,
    timeout_seconds: float | None = None,
    client: httpx.Client | None = None,
    user_agent: str | None = None,
) -> FetchedSource:
    """
    Fetch a URL and return a :class:`FetchedSource`.

    Retry strategy on HTTP 403:
    - First attempt uses the configured (bot-identifying) User-Agent.
    - On a 403, automatically retries with a randomised browser-grade UA and
      full browser request headers.  This resolves many servers that simply
      block non-browser User-Agent strings without using Cloudflare.
    - If the retry is also 403 and Cloudflare signals are detected, raises a
      descriptive :class:`SourceFetchError` that includes a hint for users.
    """
    owns_client = client is None
    settings = get_settings()
    timeout = timeout_seconds if timeout_seconds is not None else settings.scraper_request_timeout
    ua = user_agent or settings.scraper_user_agent

    http_client = client or httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": ua},
    )

    def _do_get(target_url: str, extra_headers: dict | None = None) -> httpx.Response:
        try:
            if extra_headers:
                return http_client.get(target_url, headers=extra_headers)
            return http_client.get(target_url)
        except httpx.TimeoutException as exc:
            raise SourceFetchError(f"Request timed out for {target_url}") from exc
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"Request failed for {target_url}: {exc}") from exc

    try:
        response = _do_get(url)

        # --- 403 retry with browser headers (only when we own the client) ---
        if response.status_code == 403 and owns_client:
            browser_ua = random.choice(_BROWSER_USER_AGENTS)
            browser_headers = {**_BROWSER_HEADERS, "User-Agent": browser_ua}
            retry_client = httpx.Client(
                follow_redirects=True,
                timeout=timeout,
                headers={"User-Agent": browser_ua},
            )
            try:
                response = retry_client.get(url, headers=browser_headers)
            except (httpx.TimeoutException, httpx.HTTPError):
                pass  # keep original 403 response
            finally:
                retry_client.close()

        if response.status_code == 200:
            return FetchedSource(
                requested_url=url,
                final_url=str(response.url),
                status_code=response.status_code,
                content_type=response.headers.get("content-type", ""),
                body=response.text,
                fetched_at=datetime.now(timezone.utc),
            )

        # Build a descriptive error for non-200 responses
        if response.status_code == 403:
            if _is_cloudflare_challenge(response):
                detail = (
                    "Cloudflare WAF challenge detected. This site requires JavaScript "
                    "execution in a real browser to access job listings. "
                    "Headless/static HTTP scraping is blocked by the site's anti-bot protection."
                )
            else:
                detail = (
                    "HTTP 403 Forbidden. The server is blocking automated requests. "
                    "The site may require specific cookies, session tokens, or browser-level "
                    "JavaScript execution to access this page."
                )
            raise SourceFetchError(
                f"source restricted: {detail} ({url})",
                status_code=403,
            )

        category = {
            404: "source not found",
            429: "source rate limited",
        }.get(response.status_code, "source returned an error")
        raise SourceFetchError(
            f"{category}: HTTP {response.status_code} for {url}",
            status_code=response.status_code,
        )

    finally:
        if owns_client:
            http_client.close()
