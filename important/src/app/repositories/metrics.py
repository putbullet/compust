from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import ScrapeTarget, ScrapingRun
from ..schemas_metrics import ScraperTelemetryRead


def get_scraper_telemetry(db: Session) -> ScraperTelemetryRead:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Total and status breakdowns
    runs = list(db.scalars(select(ScrapingRun).order_by(ScrapingRun.id.desc())).all())
    total_runs = len(runs)

    runs_by_status: dict[str, int] = {
        "success": 0,
        "failed": 0,
        "partial": 0,
        "running": 0,
        "pending": 0,
    }
    durations: list[float] = []
    total_jobs_found = 0
    total_jobs_added = 0
    total_jobs_updated = 0
    recent_errors: list[dict[str, str]] = []

    for r in runs:
        st = r.status.lower() if r.status else "pending"
        runs_by_status[st] = runs_by_status.get(st, 0) + 1

        if r.finished_at and r.started_at:
            duration = (r.finished_at - r.started_at).total_seconds()
            if duration >= 0:
                durations.append(duration)

        total_jobs_found += r.jobs_found or 0
        total_jobs_added += r.jobs_added or 0
        total_jobs_updated += r.jobs_updated or 0

        if r.error_message and len(recent_errors) < 5:
            recent_errors.append(
                {
                    "run_id": str(r.id),
                    "company_id": str(r.company_id),
                    "started_at": r.started_at.isoformat() if r.started_at else "",
                    "error": r.error_message,
                }
            )

    completed_runs = (
        runs_by_status.get("success", 0)
        + runs_by_status.get("failed", 0)
        + runs_by_status.get("partial", 0)
    )
    success_rate = (
        round((runs_by_status.get("success", 0) / completed_runs) * 100, 1)
        if completed_runs > 0
        else 100.0
    )
    avg_duration = (
        round(sum(durations) / len(durations), 2) if durations else 0.0
    )
    total_persisted = total_jobs_added + total_jobs_updated
    dup_rate = (
        round((total_jobs_updated / total_persisted) * 100, 1)
        if total_persisted > 0
        else 0.0
    )

    # 2. Target metrics
    targets = list(db.scalars(select(ScrapeTarget)).all())
    total_targets = len(targets)
    active_targets = sum(1 for t in targets if t.active)
    cooldown_targets = sum(
        1 for t in targets if t.cooldown_until and t.cooldown_until > now
    )
    robots_blocked = sum(
        1 for t in targets if t.robots_txt_allowed is False
    )

    return ScraperTelemetryRead(
        total_runs=total_runs,
        runs_by_status=runs_by_status,
        success_rate_percent=success_rate,
        avg_duration_seconds=avg_duration,
        total_jobs_found=total_jobs_found,
        total_jobs_added=total_jobs_added,
        total_jobs_updated=total_jobs_updated,
        duplicate_rate_percent=dup_rate,
        total_targets=total_targets,
        active_targets=active_targets,
        cooldown_targets=cooldown_targets,
        robots_blocked_targets=robots_blocked,
        recent_errors=recent_errors,
    )
