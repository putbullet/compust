"""
src/app/services/scheduler.py
==============================
Central Automatic Sync Scheduler for Compust.

Features:
- In-process asyncio background scheduler loop (Path A).
- Catch-up semantics: computes missed occurrences between last_success_at and now in the user's local timezone.
- Coalesces multiple missed occurrences into a single run.
- Runs Companies Scraper with politeness/rate limits + GitHub Internships Sync with ETag/conditional caching.
- Safe stale retirement (never touches user-tracked/applied/saved jobs; aborts if count collapses > 50%).
- Run history tracking (last 50 runs).
- Exclusivity lock preventing concurrent executions across instances.
- Injectable with Central Clock for fast, deterministic time-travel tests.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, date, time, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any
import zoneinfo

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..paths import get_storage_dir
from ..logging import get_logger
from ..database import SessionLocal
from .clock import get_clock, Clock

logger = get_logger("services.scheduler")


# ─── Configuration & State Schemas ────────────────────────────────────────────

class ScheduleConfig(BaseModel):
    enabled: bool = True
    days_of_week: list[int] = Field(default=[0, 4], description="0=Monday, 4=Friday (twice a week)")
    preferred_hour: int = Field(default=9, ge=0, le=23, description="Preferred local hour (0-23)")
    preferred_minute: int = Field(default=0, ge=0, le=59, description="Preferred local minute (0-59)")
    max_days_safety_net: int = Field(default=5, ge=1, le=30, description="Run if > N days since last success")
    timezone: str | None = Field(default=None, description="User local timezone (None = auto-detect)")
    stale_job_missed_runs: int = Field(default=2, ge=1, le=10, description="Consecutive missed runs before retiring untracked jobs")
    stale_job_max_age_days: int = Field(default=60, ge=7, le=365, description="Max age for untracked jobs in days")


class JobTypeState(BaseModel):
    last_success_at: str | None = None
    last_attempt_at: str | None = None
    last_status: str = "never_run"  # "success", "failed", "partial", "never_run", "running"
    next_due_at: str | None = None
    consecutive_failures: int = 0
    last_jobs_new: int = 0
    last_jobs_updated: int = 0
    last_jobs_retired: int = 0
    last_error: str | None = None


class RunHistoryEntry(BaseModel):
    id: str
    started_at: str
    finished_at: str
    trigger: str  # "scheduled", "manual", "catch_up", "first_run"
    status: str  # "success", "partial", "failed"
    companies_scraped: int = 0
    jobs_new: int = 0
    jobs_updated: int = 0
    jobs_retired: int = 0
    internships_synced: int = 0
    error: str | None = None


class SchedulerState(BaseModel):
    last_opened_at: str | None = None
    last_closed_at: str | None = None
    config: ScheduleConfig = Field(default_factory=ScheduleConfig)
    companies_scrape: JobTypeState = Field(default_factory=JobTypeState)
    internships_sync: JobTypeState = Field(default_factory=JobTypeState)
    history: list[RunHistoryEntry] = Field(default_factory=list)


# ─── File-based State Storage ────────────────────────────────────────────────

def get_scheduler_state_file() -> Path:
    return get_storage_dir() / "scheduler_state.json"


def get_scheduler_lock_file() -> Path:
    return get_storage_dir() / "scheduler.lock"


def load_scheduler_state() -> SchedulerState:
    path = get_scheduler_state_file()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SchedulerState(**data)
        except Exception as exc:
            logger.warning(f"Failed to read scheduler state file, using defaults: {exc}")
    return SchedulerState()


def save_scheduler_state(state: SchedulerState) -> None:
    path = get_scheduler_state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(), f, indent=2)
        os.replace(temp_path, path)
    except Exception as exc:
        logger.error(f"Failed to save scheduler state: {exc}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


# ─── Due State & Catch-Up Evaluation ──────────────────────────────────────────

def compute_next_due_local(
    config: ScheduleConfig,
    from_local_dt: datetime,
) -> datetime:
    """
    Computes the next scheduled occurrence strictly after from_local_dt in local timezone.
    """
    current_date = from_local_dt.date()
    pref_time = time(config.preferred_hour, config.preferred_minute)

    # Check today first if preferred time has not passed yet
    if current_date.weekday() in config.days_of_week:
        candidate = datetime.combine(current_date, pref_time, tzinfo=from_local_dt.tzinfo)
        if candidate > from_local_dt:
            return candidate

    # Look ahead day by day for the next scheduled weekday
    for day_offset in range(1, 8):
        future_date = current_date + timedelta(days=day_offset)
        if future_date.weekday() in config.days_of_week:
            return datetime.combine(future_date, pref_time, tzinfo=from_local_dt.tzinfo)

    # Fallback: tomorrow
    return datetime.combine(current_date + timedelta(days=1), pref_time, tzinfo=from_local_dt.tzinfo)


def evaluate_schedule_due(
    config: ScheduleConfig,
    state: JobTypeState,
    clock: Clock | None = None,
) -> dict[str, Any]:
    """
    Evaluates whether a job type is due to run, applying the Catch-Up semantics:
    - If disabled -> not due.
    - If never run (last_success_at is None and last_attempt_at is None) -> first run due.
    - If safety net triggered (> max_days_safety_net since last success) -> due.
    - If at least one scheduled slot was missed between last_success and now -> due once (coalesced).
    - If due today on/after preferred time and has not run on/after that slot -> due.
    - If already ran on/after the latest due slot -> not due.
    """
    if clock is None:
        clock = get_clock()

    if not config.enabled:
        return {
            "due": False,
            "reason": "disabled",
            "next_due_at": None,
        }

    now_utc = clock.now()
    local_now = clock.local_now(config.timezone)

    # Calculate next scheduled boundary after now
    next_due_local = compute_next_due_local(config, local_now)
    next_due_utc = clock.to_utc(next_due_local)

    # 1. First-ever launch
    if state.last_success_at is None:
        if state.last_attempt_at is None:
            return {
                "due": True,
                "reason": "first_run",
                "next_due_at": next_due_utc.isoformat(),
            }
        # If it attempted but failed, check exponential back-off
        try:
            last_att = datetime.fromisoformat(state.last_attempt_at)
            if last_att.tzinfo is None:
                last_att = last_att.replace(tzinfo=timezone.utc)
            # If failed recently, give it 15 minutes before retry
            if (now_utc - last_att).total_seconds() < 900 and state.consecutive_failures < 5:
                return {
                    "due": False,
                    "reason": "retry_backoff",
                    "next_due_at": next_due_utc.isoformat(),
                }
            return {
                "due": True,
                "reason": "first_run_retry",
                "next_due_at": next_due_utc.isoformat(),
            }
        except Exception:
            return {"due": True, "reason": "first_run", "next_due_at": next_due_utc.isoformat()}

    # 2. Parse last success
    try:
        last_success_utc = datetime.fromisoformat(state.last_success_at)
        if last_success_utc.tzinfo is None:
            last_success_utc = last_success_utc.replace(tzinfo=timezone.utc)
    except Exception:
        return {"due": True, "reason": "invalid_last_success", "next_due_at": next_due_utc.isoformat()}

    # Anomaly protection: Clock moving backwards
    if now_utc < last_success_utc:
        logger.warning(
            f"Clock moved backward: now ({now_utc.isoformat()}) < last_success ({last_success_utc.isoformat()}). "
            "Skipping duplicate execution to ensure monotonicity."
        )
        return {
            "due": False,
            "reason": "clock_anomaly_backwards",
            "next_due_at": next_due_utc.isoformat(),
        }

    # 3. Safety net: more than N days since last success
    days_since_success = (now_utc - last_success_utc).total_seconds() / 86400.0
    if days_since_success >= config.max_days_safety_net:
        return {
            "due": True,
            "reason": "safety_net_exceeded",
            "next_due_at": next_due_utc.isoformat(),
        }

    # 4. Scheduled occurrences between last_success and local_now
    last_success_local = clock.to_local(last_success_utc, config.timezone)
    pref_time = time(config.preferred_hour, config.preferred_minute)

    # Check each day from last_success_local.date() to local_now.date()
    curr_date = last_success_local.date()
    end_date = local_now.date()

    missed_count = 0
    due_today = False

    while curr_date <= end_date:
        if curr_date.weekday() in config.days_of_week:
            slot_dt = datetime.combine(curr_date, pref_time, tzinfo=local_now.tzinfo)
            if slot_dt > last_success_local and slot_dt <= local_now:
                if curr_date == end_date:
                    due_today = True
                else:
                    missed_count += 1
        curr_date += timedelta(days=1)

    if missed_count > 0:
        return {
            "due": True,
            "reason": f"catch_up_missed_{missed_count}_runs",
            "next_due_at": next_due_utc.isoformat(),
        }

    if due_today:
        return {
            "due": True,
            "reason": "scheduled_today",
            "next_due_at": next_due_utc.isoformat(),
        }

    return {
        "due": False,
        "reason": "up_to_date",
        "next_due_at": next_due_utc.isoformat(),
    }


# ─── Synchronization Engine ──────────────────────────────────────────────────

class SyncExecutionResult(BaseModel):
    success: bool
    trigger: str
    companies_scraped: int = 0
    jobs_new: int = 0
    jobs_updated: int = 0
    jobs_retired: int = 0
    internships_synced: int = 0
    errors: list[str] = Field(default_factory=list)


def execute_sync_run(
    trigger: str = "scheduled",
    clock: Clock | None = None,
) -> SyncExecutionResult:
    """
    Executes the unified sync run (Companies Scrape + GitHub Internships Sync + Safe Stale Retirement).
    Acquires exclusivity lock to prevent overlapping runs.
    """
    if clock is None:
        clock = get_clock()

    now_iso = clock.now().isoformat()
    state = load_scheduler_state()
    config = state.config

    # Exclusivity lock check
    lock_file = get_scheduler_lock_file()
    if lock_file.exists():
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(lock_file), tz=timezone.utc)
            # If lock is older than 20 minutes, treat as stale from crashed process
            if (clock.now() - mtime).total_seconds() > 1200:
                logger.warning("Removing stale scheduler lock file (>20m old).")
                lock_file.unlink(missing_ok=True)
            else:
                logger.info("Sync already in progress (lock held). Skipping duplicate invocation.")
                return SyncExecutionResult(
                    success=False,
                    trigger=trigger,
                    errors=["Sync already in progress in another worker."],
                )
        except Exception:
            pass

    try:
        lock_file.write_text(f"pid={os.getpid()} start={now_iso}\n", encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Could not write lock file: {exc}")

    result = SyncExecutionResult(success=True, trigger=trigger)
    start_time = clock.now()

    # Update attempt timestamps
    state.companies_scrape.last_attempt_at = now_iso
    state.companies_scrape.last_status = "running"
    state.internships_sync.last_attempt_at = now_iso
    state.internships_sync.last_status = "running"
    save_scheduler_state(state)

    try:
        with SessionLocal() as db:
            from ..repositories.companies import get_company
            from ..repositories.scrape_targets import list_scrape_targets, get_scrape_target
            from ..scraper.service import (
                verify_target_robots_compliance,
                is_in_cooldown,
                get_strategy_for_target,
                start_scraping_run,
                crawl_pages,
                persist_candidates,
                finish_scraping_run,
                apply_target_outcome,
                ScrapingRunScope,
            )
            from .stale_lifecycle import evaluate_target_stale_jobs

            targets = list_scrape_targets(db)
            active_targets = [t for t in targets if t.status in ("active", "healthy", "pending", None)]

            for target in active_targets:
                try:
                    if not verify_target_robots_compliance(db, target):
                        continue
                    in_cooldown, _ = is_in_cooldown(target)
                    if in_cooldown:
                        continue

                    company = get_company(db, target.company_id)
                    strategy = get_strategy_for_target(target, company)
                    if strategy is None or not company or not company.countries:
                        continue

                    run = start_scraping_run(db, target.company_id)
                    with ScrapingRunScope(scraping_run_id=run.id, company_id=target.company_id, target_id=target.id):
                        try:
                            crawl_result = crawl_pages(target.url, strategy, max_pages=5)
                            added, updated = persist_candidates(
                                db,
                                company_id=target.company_id,
                                country_id=company.countries[0].id,
                                source=strategy.source_name,
                                candidates=crawl_result.jobs,
                                scrape_target_id=target.id,
                            )
                            finish_scraping_run(
                                db,
                                run,
                                jobs_found=len(crawl_result.jobs),
                                jobs_added=added,
                                jobs_updated=updated,
                                parser_errors=crawl_result.errors,
                            )
                            outcome = "partial" if crawl_result.errors else "success"
                            apply_target_outcome(db, target, outcome)

                            # Safe Stale Job Evaluation
                            if not crawl_result.errors and len(crawl_result.jobs) > 0:
                                seen_ext = {c.external_job_id for c in crawl_result.jobs if c.external_job_id}
                                seen_urls = {c.job_url for c in crawl_result.jobs if c.job_url}
                                retired = evaluate_target_stale_jobs(
                                    db,
                                    company_id=target.company_id,
                                    scrape_target_id=target.id,
                                    seen_external_ids=seen_ext,
                                    seen_urls=seen_urls,
                                    is_full_success=True,
                                    max_missed_runs=config.stale_job_missed_runs,
                                    max_age_days=config.stale_job_max_age_days,
                                )
                                result.jobs_retired += retired

                            result.companies_scraped += 1
                            result.jobs_new += added
                            result.jobs_updated += updated
                        except Exception as e:
                            finish_scraping_run(db, run, request_error=str(e), forced_status="failed")
                            apply_target_outcome(db, target, "failed")
                            result.errors.append(f"Target {target.id} failed: {e}")
                except Exception as exc:
                    result.errors.append(f"Company scrape target #{target.id} exception: {exc}")

        # 2. Sync GitHub Internships
        try:
            from .github_internships_service import GitHubInternshipsService
            service = GitHubInternshipsService()
            internships_resp = service.sync_all_repos()
            result.internships_synced = len(internships_resp.items)
        except Exception as exc:
            result.errors.append(f"GitHub internships sync failed: {exc}")

        # 3. Compute final statuses & persist runtime state
        finish_time = clock.now()
        success = len(result.errors) == 0

        # Update companies_scrape state
        state.companies_scrape.last_status = "success" if success else ("partial" if result.companies_scraped > 0 else "failed")
        if state.companies_scrape.last_status in ("success", "partial"):
            state.companies_scrape.last_success_at = finish_time.isoformat()
            state.companies_scrape.consecutive_failures = 0
        else:
            state.companies_scrape.consecutive_failures += 1
        state.companies_scrape.last_jobs_new = result.jobs_new
        state.companies_scrape.last_jobs_updated = result.jobs_updated
        state.companies_scrape.last_jobs_retired = result.jobs_retired
        state.companies_scrape.last_error = "; ".join(result.errors) if result.errors else None

        # Update internships_sync state
        state.internships_sync.last_status = "success" if result.internships_synced > 0 else "failed"
        if state.internships_sync.last_status == "success":
            state.internships_sync.last_success_at = finish_time.isoformat()
            state.internships_sync.consecutive_failures = 0
        else:
            state.internships_sync.consecutive_failures += 1

        # Calculate next due time
        local_now = clock.local_now(config.timezone)
        next_due_local = compute_next_due_local(config, local_now)
        next_due_utc = clock.to_utc(next_due_local).isoformat()
        state.companies_scrape.next_due_at = next_due_utc
        state.internships_sync.next_due_at = next_due_utc

        # Record history
        entry = RunHistoryEntry(
            id=f"run-{int(start_time.timestamp())}",
            started_at=start_time.isoformat(),
            finished_at=finish_time.isoformat(),
            trigger=trigger,
            status="success" if success else ("partial" if (result.companies_scraped > 0 or result.internships_synced > 0) else "failed"),
            companies_scraped=result.companies_scraped,
            jobs_new=result.jobs_new,
            jobs_updated=result.jobs_updated,
            jobs_retired=result.jobs_retired,
            internships_synced=result.internships_synced,
            error="; ".join(result.errors) if result.errors else None,
        )
        state.history.insert(0, entry)
        state.history = state.history[:50]  # keep last 50 entries
        save_scheduler_state(state)

        result.success = success or (result.companies_scraped > 0 or result.internships_synced > 0)
        return result

    finally:
        # Release exclusivity lock
        try:
            if lock_file.exists():
                lock_file.unlink()
        except Exception:
            pass


# ─── Background Asyncio Scheduler Loop ───────────────────────────────────────

class AutoSyncScheduler:
    """Manages the in-process asyncio background loop."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running: bool = False
        self._interval_seconds: float = 900.0  # 15 minutes periodic tick

    def start(self, initial_delay: float = 5.0) -> None:
        """Starts the scheduler background task."""
        if self._running:
            return
        self._running = True
        state = load_scheduler_state()
        state.last_opened_at = get_clock().now().isoformat()
        save_scheduler_state(state)

        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run_loop(initial_delay))
        logger.info("AutoSyncScheduler background task started.")

    def stop(self) -> None:
        """Stops the scheduler cleanly."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        state = load_scheduler_state()
        state.last_closed_at = get_clock().now().isoformat()
        save_scheduler_state(state)
        logger.info("AutoSyncScheduler background task stopped.")

    async def _run_loop(self, initial_delay: float) -> None:
        try:
            if initial_delay > 0:
                await asyncio.sleep(initial_delay)

            # Startup catch-up check
            self._check_and_trigger("startup_catch_up")

            while self._running:
                await asyncio.sleep(self._interval_seconds)
                self._check_and_trigger("periodic_tick")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"Scheduler loop encountered unexpected error: {exc}")

    def _check_and_trigger(self, trigger_name: str) -> None:
        try:
            state = load_scheduler_state()
            due_res = evaluate_schedule_due(state.config, state.companies_scrape)
            if due_res.get("due"):
                logger.info(f"AutoSyncScheduler triggering sync ({trigger_name}: {due_res.get('reason')}).")
                # Run execution in threadpool to avoid blocking event loop
                asyncio.to_thread(execute_sync_run, trigger=trigger_name)
        except Exception as exc:
            logger.error(f"Error checking schedule: {exc}")


_SCHEDULER_INSTANCE: AutoSyncScheduler | None = None


def get_scheduler() -> AutoSyncScheduler:
    global _SCHEDULER_INSTANCE
    if _SCHEDULER_INSTANCE is None:
        _SCHEDULER_INSTANCE = AutoSyncScheduler()
    return _SCHEDULER_INSTANCE
