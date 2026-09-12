from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
import urllib.robotparser

from sqlalchemy.orm import Session

from ..models import ScrapeTarget
from .http_client import SourceFetchError, fetch_source


class RobotsDisallowedError(Exception):
    """Raised when a target path is disallowed by robots.txt."""
    pass


def get_robots_txt_url(target_url: str) -> str:
    parsed = urlsplit(target_url)
    return urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))


def is_path_allowed_by_robots(target_url: str, user_agent: str = "CompustBot") -> bool:
    """Fetch and parse robots.txt for the target domain and check if the target URL path is permitted."""
    robots_url = get_robots_txt_url(target_url)
    try:
        source = fetch_source(robots_url)
        rfp = urllib.robotparser.RobotFileParser()
        rfp.parse(source.body.splitlines())
        # Check specific user agent, then fallback to wildcard
        allowed = rfp.can_fetch(user_agent, target_url)
        if allowed is None:
            allowed = rfp.can_fetch("*", target_url)
        return bool(allowed)
    except SourceFetchError as exc:
        # If robots.txt returns 404 / 410, robots convention considers everything allowed
        if exc.status_code in (404, 410):
            return True
        # If 403 or server error, be cautious
        if exc.status_code == 403:
            return False
        # For transient network errors fetching robots.txt, assume allowed but log
        return True


def verify_target_robots_compliance(
    db: Session,
    target: ScrapeTarget,
    user_agent: str = "CompustBot",
    force_refresh: bool = False,
) -> bool:
    """Verify target against robots.txt, update scrape_targets row, and flag SOURCE_DISALLOWED if blocked."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    checked_at = getattr(target, "robots_txt_checked_at", None)
    cached_allowed = getattr(target, "robots_txt_allowed", None)

    # Cache check for 24 hours unless forced
    if (
        not force_refresh
        and checked_at is not None
        and cached_allowed is not None
    ):
        elapsed = (now - checked_at).total_seconds()
        if elapsed < 86400:
            if not cached_allowed:
                if hasattr(target, "status"):
                    target.status = "SOURCE_DISALLOWED"
                if hasattr(db, "commit"):
                    db.commit()
                return False
            return True

    allowed = is_path_allowed_by_robots(target.url, user_agent=user_agent)
    if hasattr(target, "robots_txt_allowed"):
        target.robots_txt_allowed = allowed
    if hasattr(target, "robots_txt_checked_at"):
        target.robots_txt_checked_at = now
    if not allowed and hasattr(target, "status"):
        target.status = "SOURCE_DISALLOWED"
    if hasattr(db, "commit"):
        db.commit()

    return allowed
