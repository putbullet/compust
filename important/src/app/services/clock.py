"""
src/app/services/clock.py
=========================
Central Clock Service for Compust.
Single authoritative source of time for all scheduling, freshness, and aging code.

Rules:
- Never call raw datetime.now() directly in scheduling or aging code.
- All stored timestamps are in UTC.
- Schedule boundaries and user-facing dates are computed in the user's local timezone.
- Injectable for testing (FrozenClock for deterministic time-travel tests).
- Detects and logs clock setbacks/anomalies without failing.
- No external time servers (local-first).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any
import zoneinfo

from ..logging import get_logger

logger = get_logger("services.clock")


class Clock(ABC):
    """Abstract Central Clock Interface."""

    @abstractmethod
    def now(self) -> datetime:
        """Returns the current timezone-aware UTC datetime."""
        pass

    def now_naive(self) -> datetime:
        """Returns current UTC datetime without tzinfo (for naive SQLite columns)."""
        return self.now().replace(tzinfo=None)

    def local_now(self, tz_name: str | None = None) -> datetime:
        """Returns the current datetime converted to the requested or local timezone."""
        target_tz = self.get_timezone(tz_name)
        return self.now().astimezone(target_tz)

    def to_local(self, dt: datetime, tz_name: str | None = None) -> datetime:
        """Converts an arbitrary datetime to the local timezone. Assumes UTC if naive."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        target_tz = self.get_timezone(tz_name)
        return dt.astimezone(target_tz)

    def to_utc(self, dt: datetime) -> datetime:
        """Converts any datetime to timezone-aware UTC."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def get_timezone(self, tz_name: str | None = None) -> zoneinfo.ZoneInfo:
        """Resolves a timezone name to a ZoneInfo object, falling back to UTC if invalid."""
        if tz_name:
            try:
                return zoneinfo.ZoneInfo(tz_name)
            except Exception as exc:
                logger.warning(f"Invalid timezone '{tz_name}', falling back to local: {exc}")

        # Fallback to system local zone
        try:
            local_tz = datetime.now().astimezone().tzinfo
            if local_tz is not None:
                tz_str = str(local_tz)
                # Try creating ZoneInfo from string
                try:
                    return zoneinfo.ZoneInfo(tz_str)
                except Exception:
                    pass
                if hasattr(local_tz, "key") and local_tz.key:
                    return zoneinfo.ZoneInfo(local_tz.key)
        except Exception:
            pass

        try:
            return zoneinfo.ZoneInfo("UTC")
        except Exception:
            return timezone.utc

    def system_timezone_name(self) -> str:
        """Returns the name of the system timezone."""
        try:
            local_tz = datetime.now().astimezone().tzinfo
            if local_tz is not None:
                if hasattr(local_tz, "key") and local_tz.key:
                    return str(local_tz.key)
                return str(local_tz)
        except Exception:
            pass
        return "UTC"


class RealClock(Clock):
    """Production Clock backed by the operating system time."""

    def __init__(self) -> None:
        self._last_observed_utc: datetime | None = None

    def now(self) -> datetime:
        current_utc = datetime.now(timezone.utc)
        if self._last_observed_utc is not None:
            # Anomaly detection: clock jumped backwards by more than 10 seconds
            if current_utc < self._last_observed_utc - timedelta(seconds=10):
                diff = (self._last_observed_utc - current_utc).total_seconds()
                logger.warning(
                    f"Clock anomaly detected: time moved backward by {diff:.1f}s. "
                    "Compust scheduling ensures monotonicity."
                )
        self._last_observed_utc = current_utc
        return current_utc


class FrozenClock(Clock):
    """Test-injectable clock allowing deterministic time-travel and freezing."""

    def __init__(self, initial_time: datetime | None = None, default_tz: str = "UTC") -> None:
        if initial_time is None:
            self._current_utc = datetime(2026, 10, 19, 9, 0, 0, tzinfo=timezone.utc)  # Monday 09:00 UTC
        elif initial_time.tzinfo is None:
            self._current_utc = initial_time.replace(tzinfo=timezone.utc)
        else:
            self._current_utc = initial_time.astimezone(timezone.utc)

        self._default_tz = default_tz

    def now(self) -> datetime:
        return self._current_utc

    def set_time(self, dt: datetime) -> None:
        if dt.tzinfo is None:
            self._current_utc = dt.replace(tzinfo=timezone.utc)
        else:
            self._current_utc = dt.astimezone(timezone.utc)

    def advance(
        self,
        *,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        days: float = 0,
    ) -> datetime:
        delta = timedelta(
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            days=days,
        )
        self._current_utc += delta
        return self._current_utc

    def system_timezone_name(self) -> str:
        return self._default_tz

    def get_timezone(self, tz_name: str | None = None) -> zoneinfo.ZoneInfo:
        target = tz_name or self._default_tz
        try:
            return zoneinfo.ZoneInfo(target)
        except Exception:
            try:
                return zoneinfo.ZoneInfo("UTC")
            except Exception:
                return timezone.utc


# Global clock singleton
_GLOBAL_CLOCK: Clock = RealClock()


def get_clock() -> Clock:
    """Returns the active clock singleton."""
    return _GLOBAL_CLOCK


def set_clock(clock: Clock) -> None:
    """Overrides the active clock singleton (used in test fixtures)."""
    global _GLOBAL_CLOCK
    _GLOBAL_CLOCK = clock


def reset_clock() -> None:
    """Resets the active clock back to the RealClock."""
    global _GLOBAL_CLOCK
    _GLOBAL_CLOCK = RealClock()
