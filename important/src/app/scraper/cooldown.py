from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from ..models import ScrapeTarget

COOLDOWN_DURATIONS = {
    "rate_limited": timedelta(hours=1),
    "restricted": timedelta(hours=6),
    "timeout": timedelta(minutes=15),
    "connection_error": timedelta(minutes=15),
    "parser_error": timedelta(minutes=30),
    "partial": timedelta(minutes=5),
}


def is_in_cooldown(target: ScrapeTarget) -> tuple[bool, str | None]:
    """Check if the scrape target is currently in cooldown."""
    if not target.cooldown_until:
        return False, None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if target.cooldown_until > now:
        remaining_seconds = int((target.cooldown_until - now).total_seconds())
        message = (
            f"Scrape target is in cooldown until {target.cooldown_until.isoformat()} "
            f"({remaining_seconds}s remaining, status: {target.status})"
        )
        return True, message

    return False, None


def apply_target_outcome(
    db: Session,
    target: ScrapeTarget,
    outcome: str,
    *,
    custom_cooldown: timedelta | None = None,
) -> datetime | None:
    """
    Update scrape target status and set cooldown depending on outcome:
    - rate_limited (429) -> 1 hour
    - restricted (403) -> 6 hours
    - timeout -> 15 min
    - connection_error -> 15 min
    - parser_error -> 30 min
    - success -> clears cooldown
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    target.last_scraped_at = now
    target.status = outcome

    if outcome == "success":
        target.cooldown_until = None
    else:
        duration = custom_cooldown or COOLDOWN_DURATIONS.get(outcome, timedelta(minutes=15))
        target.cooldown_until = now + duration

    if hasattr(db, "add"):
        db.add(target)
    if hasattr(db, "commit"):
        db.commit()
    if hasattr(db, "refresh"):
        db.refresh(target)
    return target.cooldown_until
