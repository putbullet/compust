from datetime import datetime, timezone
import logging
from typing import Any

from ..config import get_settings
from .http_client import FetchedSource, SourceFetchError

logger = logging.getLogger(__name__)

_DEFAULT_CHROMIUM_ARGS = [
    "--disable-gpu",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-zygote",
    "--disable-extensions",
]


def is_playwright_available() -> bool:
    """Check if Playwright is installed and importable in the current environment."""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_rendered_source(
    url: str,
    *,
    timeout_seconds: float | None = None,
    wait_until: str = "networkidle",
    block_resources: bool = True,
    headless: bool | None = None,
) -> FetchedSource:
    """
    Launch a headless browser via Playwright to fully execute client-side
    JavaScript and render Single Page Applications (SPAs) before parsing.

    Intercepts and blocks non-essential assets (images, media, fonts) to keep
    rendering speed fast and minimize network resource usage.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
    except ImportError as exc:
        raise SourceFetchError(
            f"Playwright is not installed in the environment: {exc}. Run 'pip install playwright && playwright install chromium'."
        ) from exc

    settings = get_settings()
    timeout = timeout_seconds if timeout_seconds is not None else settings.scraper_browser_timeout_seconds
    is_headless = headless if headless is not None else settings.scraper_browser_headless
    timeout_ms = int(timeout * 1000)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=is_headless,
                args=_DEFAULT_CHROMIUM_ARGS,
            )
            try:
                context = browser.new_context(
                    user_agent=settings.scraper_user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    bypass_csp=True,
                )
                page = context.new_page()

                if block_resources:
                    def _route_filter(route: Any) -> None:
                        if route.request.resource_type in ("image", "media", "font"):
                            try:
                                route.abort()
                            except Exception:
                                pass
                        else:
                            try:
                                route.continue_()
                            except Exception:
                                pass

                    page.route("**/*", _route_filter)

                # Navigate with domcontentloaded to avoid hanging on persistent connections
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

                # Attempt to wait for network idle to allow SPA hydration
                try:
                    page.wait_for_load_state(wait_until, timeout=min(5000, timeout_ms))
                except Exception:
                    # Non-fatal if network idle times out (e.g. active websocket / polling)
                    pass

                # Brief tick for DOM stabilization
                page.wait_for_timeout(300)

                body_content = page.content()
                final_url = page.url or url

                return FetchedSource(
                    requested_url=url,
                    final_url=final_url,
                    status_code=200,
                    content_type="text/html; charset=utf-8",
                    body=body_content,
                    fetched_at=datetime.now(timezone.utc),
                    is_rendered=True,
                )
            finally:
                browser.close()

    except PlaywrightTimeoutError as exc:
        raise SourceFetchError(f"Playwright browser rendering timed out after {timeout}s for {url}: {exc}") from exc
    except PlaywrightError as exc:
        raise SourceFetchError(f"Playwright browser rendering error for {url}: {exc}") from exc
    except Exception as exc:
        raise SourceFetchError(f"Unexpected browser rendering failure for {url}: {exc}") from exc
