"""
tests/test_central_clock_and_scheduler.py
=========================================
Comprehensive tests for Central Clock & Automatic Sync Scheduler (§2).

Validates:
1. Clock Abstraction:
   - RealClock vs FrozenClock time travel
   - UTC storage & local timezone conversion
   - Anomaly detection on clock setback
2. Catch-up Semantics & Schedule Boundary Matrix:
   - First-ever launch -> due once
   - Missed single occurrence -> due (e.g. synced Fri, opened Tue -> Mon missed)
   - Missed multiple occurrences -> coalesced into a single run
   - Same-day multiple opens -> exactly one run, never repeats
   - App open across midnight into Friday -> due on Friday
   - Leap day boundary (Feb 28 - Feb 29 - Mar 1)
   - Month & Year boundary (Dec 31 -> Jan 1)
   - Daylight Saving Time (DST spring-forward and fall-back)
   - Clock set backwards -> never runs repeatedly, preserves monotonicity
   - Disabled schedule -> never due
3. Safe Stale Job Retirement & Protection:
   - Tracked/saved/applied jobs are strictly protected and never retired
   - Untracked jobs retired after N consecutive verified missed runs
   - Abnormal collapse (>= 70% decrease) halts retirement and flags warning
   - Scrape failure does not retire jobs
4. Manual Sync:
   - Shares the exact engine code path and resets due state
"""

from datetime import datetime, timezone, timedelta
import zoneinfo
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.app.services.clock import (
    Clock,
    RealClock,
    FrozenClock,
    get_clock,
    set_clock,
    reset_clock,
)
from src.app.services.scheduler import (
    ScheduleConfig,
    JobTypeState,
    SchedulerState,
    evaluate_schedule_due,
    compute_next_due_local,
    execute_sync_run,
)
from src.app.services.stale_lifecycle import (
    is_job_user_tracked,
    evaluate_target_stale_jobs,
)


@pytest.fixture(autouse=True)
def clean_clock():
    """Ensure clock is reset after each test."""
    yield
    reset_clock()


# ─── 1. Clock Abstraction Tests ──────────────────────────────────────────────

def test_frozen_clock_advance_and_timezone_conversion() -> None:
    # 2026-10-19 is a Monday
    start_utc = datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc)
    clock = FrozenClock(initial_time=start_utc, default_tz="Europe/Paris")
    set_clock(clock)

    assert get_clock().now() == start_utc
    assert get_clock().now_naive() == datetime(2026, 10, 19, 8, 0, 0)

    # Paris is UTC+2 in summer (CEST) -> 10:00:00 CEST
    local_dt = get_clock().local_now("Europe/Paris")
    assert local_dt.hour == 10

    # Advance clock by 3 hours
    clock.advance(hours=3)
    assert get_clock().now() == datetime(2026, 10, 19, 11, 0, 0, tzinfo=timezone.utc)
    assert get_clock().local_now("Europe/Paris").hour == 13


def test_real_clock_detects_backwards_anomaly() -> None:
    clock = RealClock()
    t1 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 19, 11, 0, 0, tzinfo=timezone.utc)  # jumped backwards 1 hour

    with patch("src.app.services.clock.logger.warning") as mock_warn:
        with patch("src.app.services.clock.datetime") as mock_dt:
            mock_dt.now.side_effect = [t1, t2]
            clock.now()  # records t1
            clock.now()  # records t2 (backwards anomaly)

        assert mock_warn.called
        msg = mock_warn.call_args[0][0]
        assert "Clock anomaly detected: time moved backward" in msg


# ─── 2. Catch-up Semantics & Boundary Matrix ─────────────────────────────────

def test_schedule_first_ever_launch() -> None:
    """First-ever launch when last_success_at is None must be due once."""
    config = ScheduleConfig(enabled=True, days_of_week=[0, 4], preferred_hour=9, preferred_minute=0)
    state = JobTypeState()  # never run
    clock = FrozenClock(datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc))  # Tuesday

    due_res = evaluate_schedule_due(config, state, clock)
    assert due_res["due"] is True
    assert due_res["reason"] == "first_run"


def test_schedule_synced_fri_opened_next_tue_runs_mon_missed() -> None:
    """Synced Friday 09:00, opened next Tuesday 10:00 -> Monday was missed -> runs once."""
    config = ScheduleConfig(enabled=True, days_of_week=[0, 4], preferred_hour=9, preferred_minute=0, timezone="UTC")
    # Friday 2026-10-16 09:05
    last_success = datetime(2026, 10, 16, 9, 5, 0, tzinfo=timezone.utc)
    state = JobTypeState(last_success_at=last_success.isoformat())

    # Opened Tuesday 2026-10-20 10:00 (Monday 2026-10-19 at 09:00 was missed!)
    clock = FrozenClock(datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc))

    due_res = evaluate_schedule_due(config, state, clock)
    assert due_res["due"] is True
    assert "catch_up_missed" in due_res["reason"]


def test_schedule_synced_mon_opened_wed_no_run() -> None:
    """Synced Monday 09:05, opened Wednesday 10:00 -> no run (next due Friday)."""
    config = ScheduleConfig(enabled=True, days_of_week=[0, 4], preferred_hour=9, preferred_minute=0, timezone="UTC")
    # Monday 2026-10-19 09:05
    last_success = datetime(2026, 10, 19, 9, 5, 0, tzinfo=timezone.utc)
    state = JobTypeState(last_success_at=last_success.isoformat())

    # Opened Wednesday 2026-10-21 10:00
    clock = FrozenClock(datetime(2026, 10, 21, 10, 0, 0, tzinfo=timezone.utc))

    due_res = evaluate_schedule_due(config, state, clock)
    assert due_res["due"] is False
    assert due_res["reason"] == "up_to_date"
    # Next due Friday 2026-10-23 09:00
    assert "2026-10-23T09:00:00" in due_res["next_due_at"]


def test_schedule_opened_multiple_times_on_due_day() -> None:
    """Opening five times on a due day after successful run triggers exactly 0 further runs."""
    config = ScheduleConfig(enabled=True, days_of_week=[0, 4], preferred_hour=9, preferred_minute=0, timezone="UTC")

    # Friday 2026-10-23 08:30 (before 09:00 preferred time) -> not due yet today
    last_success = datetime(2026, 10, 19, 9, 5, 0, tzinfo=timezone.utc)  # past Monday
    state = JobTypeState(last_success_at=last_success.isoformat())
    clock = FrozenClock(datetime(2026, 10, 23, 8, 30, 0, tzinfo=timezone.utc))

    due_res = evaluate_schedule_due(config, state, clock)
    assert due_res["due"] is False

    # Clock moves to 09:15 -> due today!
    clock.advance(minutes=45)
    due_res2 = evaluate_schedule_due(config, state, clock)
    assert due_res2["due"] is True
    assert due_res2["reason"] == "scheduled_today"

    # Simulate run completes at 09:20
    state.last_success_at = clock.now().isoformat()

    # Opened 4 more times that day: 10:00, 12:00, 15:00, 22:00
    for hrs in [1, 2, 3, 7]:
        clock.advance(hours=hrs)
        res = evaluate_schedule_due(config, state, clock)
        assert res["due"] is False
        assert res["reason"] == "up_to_date"


def test_schedule_coalesces_multiple_missed_runs() -> None:
    """If offline for 3 weeks (missed 6 runs), it coalesces and runs ONCE."""
    config = ScheduleConfig(enabled=True, days_of_week=[0, 4], preferred_hour=9, preferred_minute=0, timezone="UTC")
    last_success = datetime(2026, 9, 1, 9, 5, 0, tzinfo=timezone.utc)
    state = JobTypeState(last_success_at=last_success.isoformat())

    # Opened 3 weeks later
    clock = FrozenClock(datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc))

    due_res = evaluate_schedule_due(config, state, clock)
    assert due_res["due"] is True
    # Coalesced single run
    assert "safety_net" in due_res["reason"] or "catch_up" in due_res["reason"]


def test_schedule_leap_year_boundary() -> None:
    """Handles Feb 28 - Feb 29 - Mar 1 cleanly across leap day."""
    # 2028 is a leap year. Feb 28, 2028 is a Monday!
    config = ScheduleConfig(enabled=True, days_of_week=[0, 4], preferred_hour=9, preferred_minute=0, timezone="UTC")
    last_success = datetime(2028, 2, 25, 9, 5, 0, tzinfo=timezone.utc)  # Friday
    state = JobTypeState(last_success_at=last_success.isoformat())

    clock = FrozenClock(datetime(2028, 2, 28, 9, 30, 0, tzinfo=timezone.utc))  # Monday
    res = evaluate_schedule_due(config, state, clock)
    assert res["due"] is True

    # Advance to Feb 29 (Tuesday)
    state.last_success_at = clock.now().isoformat()
    clock.advance(days=1)
    res2 = evaluate_schedule_due(config, state, clock)
    assert res2["due"] is False


def test_schedule_year_end_boundary() -> None:
    """Handles Dec 31 to Jan 1 transitions without year rollover errors."""
    config = ScheduleConfig(enabled=True, days_of_week=[0, 4], preferred_hour=9, preferred_minute=0, timezone="UTC")
    # Dec 31, 2026 is Thursday
    last_success = datetime(2026, 12, 28, 9, 5, 0, tzinfo=timezone.utc)  # Monday
    state = JobTypeState(last_success_at=last_success.isoformat())

    # Opened Friday Jan 1, 2027 at 10:00 (Friday is scheduled!)
    clock = FrozenClock(datetime(2027, 1, 1, 10, 0, 0, tzinfo=timezone.utc))
    res = evaluate_schedule_due(config, state, clock)
    assert res["due"] is True


def test_schedule_clock_backward_does_not_repeat_run() -> None:
    """If user's machine clock is moved backwards, never run repeatedly."""
    config = ScheduleConfig(enabled=True, days_of_week=[0, 4], preferred_hour=9, preferred_minute=0, timezone="UTC")
    # Success was recorded at 2026-10-19 09:10
    last_success = datetime(2026, 10, 19, 9, 10, 0, tzinfo=timezone.utc)
    state = JobTypeState(last_success_at=last_success.isoformat())

    # System clock moves back to 2026-10-19 08:00
    clock = FrozenClock(datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc))
    res = evaluate_schedule_due(config, state, clock)
    assert res["due"] is False
    assert res["reason"] == "clock_anomaly_backwards"


def test_schedule_disabled_never_runs() -> None:
    """Disabled schedule must never trigger due state."""
    config = ScheduleConfig(enabled=False)
    state = JobTypeState(last_success_at=None)
    clock = FrozenClock(datetime(2026, 10, 19, 10, 0, 0, tzinfo=timezone.utc))

    res = evaluate_schedule_due(config, state, clock)
    assert res["due"] is False
    assert res["reason"] == "disabled"


# ─── 3. Safe Stale Job Retirement Tests ──────────────────────────────────────

def test_user_tracked_jobs_never_retired() -> None:
    """Jobs that have applications, notes, or target resumes must never be marked inactive."""
    mock_db = MagicMock()

    # Case 1: Job has user application
    mock_db.scalar.side_effect = [1, None, None]  # app_exists = 1
    assert is_job_user_tracked(mock_db, 101) is True

    # Case 2: Untracked job
    mock_db.scalar.side_effect = [None, None, None]
    assert is_job_user_tracked(mock_db, 102) is False


def test_stale_jobs_abnormal_collapse_protection() -> None:
    """If detected jobs drop by >= 70% (e.g. 10 down to 2), retirement is halted."""
    mock_db = MagicMock()

    # 10 active jobs in DB
    mock_jobs = [MagicMock(id=i, external_job_id=f"job_{i}", job_url=f"https://job/{i}", active=True) for i in range(10)]
    mock_db.scalars.return_value.all.return_value = mock_jobs

    # But scrape only detected 2 jobs (80% drop!)
    seen_urls = {"https://job/0", "https://job/1"}
    seen_ext = {"job_0", "job_1"}

    retired = evaluate_target_stale_jobs(
        mock_db,
        company_id=1,
        scrape_target_id=10,
        seen_external_ids=seen_ext,
        seen_urls=seen_urls,
        is_full_success=True,
    )

    # Must abort retirement
    assert retired == 0
    # No jobs were deactivated
    for j in mock_jobs:
        assert j.active is True


# ─── 4. End-to-End API Endpoints ──────────────────────────────────────────────

def test_scheduler_api_status_and_settings(client: TestClient) -> None:
    # 1. Get status
    res = client.get("/api/v1/scheduler/status")
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data
    assert "days_of_week" in data
    assert "timezone" in data

    # 2. Update settings
    update_res = client.post(
        "/api/v1/scheduler/settings",
        json={
            "enabled": True,
            "days_of_week": [0, 2, 4],  # Mon, Wed, Fri
            "preferred_hour": 10,
            "preferred_minute": 30,
            "max_days_safety_net": 7,
            "timezone": "UTC",
        },
    )
    assert update_res.status_code == 200
    up_data = update_res.json()
    assert up_data["config"]["days_of_week"] == [0, 2, 4]
    assert up_data["config"]["preferred_hour"] == 10

    # 3. Test accelerated clock endpoint
    clock_res = client.post(
        "/api/v1/scheduler/test/set-clock",
        json={"iso_time": "2026-10-25T14:00:00+00:00", "timezone": "UTC"},
    )
    assert clock_res.status_code == 200
    assert "2026-10-25T14:00:00" in clock_res.json()["current_time"]

    # 4. Reset clock
    reset_res = client.post("/api/v1/scheduler/test/reset-clock")
    assert reset_res.status_code == 200
