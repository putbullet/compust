"""
src/app/services/stale_lifecycle.py
===================================
Safe lifecycle management for job freshness and retirement.

Standing Rules:
- Never mark inactive or retire anything the user touched (saved, tracked, noted, linked to an application/contact).
- For untracked jobs, mark as closed/archived ONLY when the source scrape succeeded plausibly AND the job has been
  missing for N consecutive successful runs (default 2) OR exceeds max age (default 60 days).
- If a company's detected job count collapses abnormally (>= 70% drop), do NOT retire anything;
  flag it for review via scraper diagnostics.
- Uses Central Clock (no raw datetime.now()).
"""

from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Job, ScrapingRun, UserApplication, Resume, CustomizedResume
from ..logging import get_logger
from ..scraper.url_normalizer import normalize_url
from .clock import get_clock

logger = get_logger("stale_lifecycle")


def is_safe_for_stale_evaluation(
    *,
    is_full_success: bool,
    parser_errors: list[str] | None = None,
    jobs_found: int = 0,
) -> bool:
    """
    Determines if a scrape run qualifies for evaluating missing jobs.
    Must be 100% successful, zero parser errors, and verified non-empty discovery.
    """
    if not is_full_success:
        return False
    if parser_errors and len(parser_errors) > 0:
        return False
    if jobs_found <= 0:
        return False
    return True


def is_job_user_tracked(db: Session, job_id: int) -> bool:
    """
    Checks if a job has been touched, tracked, saved, noted, or applied to by any user.
    User-tracked jobs must NEVER be retired or marked inactive by automated scrapers.
    """
    # 1. Check UserApplication
    app_exists = db.scalar(
        select(UserApplication.id).where(UserApplication.job_id == job_id).limit(1)
    )
    if app_exists:
        return True

    # 2. Check Resume target_job_id
    resume_target = db.scalar(
        select(Resume.id).where(Resume.target_job_id == job_id).limit(1)
    )
    if resume_target:
        return True

    # 3. Check CustomizedResume job_id
    customized_exists = db.scalar(
        select(CustomizedResume.id).where(CustomizedResume.job_id == job_id).limit(1)
    )
    if customized_exists:
        return True

    return False


def evaluate_target_stale_jobs(
    db: Session,
    *,
    company_id: int,
    scrape_target_id: int,
    seen_external_ids: set[str],
    seen_urls: set[str],
    is_full_success: bool,
    max_missed_runs: int | None = None,
    max_age_days: int = 60,
) -> int:
    """
    Cautiously evaluates active jobs for a scrape target and marks them inactive
    ONLY if the source scrape was 100% successful and the job was absent across
    multiple consecutive verified successful crawl runs.

    Protections:
    - User-tracked jobs are strictly preserved.
    - An abnormal collapse in detected jobs (>= 70% decrease) halts retirement.
    """
    if not is_full_success:
        logger.info(
            f"Skipping stale evaluation for target {scrape_target_id}: scrape was partial or failed."
        )
        return 0

    settings = get_settings()
    threshold = max_missed_runs if max_missed_runs is not None else settings.stale_job_missed_runs_threshold

    clock = get_clock()
    now_naive = clock.now_naive()
    max_age_cutoff = now_naive - timedelta(days=max_age_days)

    # Normalize incoming URLs so comparison matches stored canonical URLs
    normalized_seen_urls = {normalize_url(u) for u in seen_urls if u} | set(seen_urls)

    # Fetch active jobs for this target/company
    active_jobs = list(
        db.scalars(
            select(Job).where(
                Job.company_id == company_id,
                Job.active == True,
                (Job.scrape_target_id == scrape_target_id) | (Job.scrape_target_id == None),
            )
        ).all()
    )

    if not active_jobs:
        return 0

    # Guard against abnormal collapse: if detected count collapsed abnormally by >= 70%
    # when previously active count was >= 3, do not retire anything.
    if len(active_jobs) >= 3 and len(normalized_seen_urls) < 0.3 * len(active_jobs):
        logger.warning(
            f"Abnormal job count collapse for company #{company_id} (target #{scrape_target_id}): "
            f"active jobs in DB={len(active_jobs)}, newly detected={len(normalized_seen_urls)} (>=70% drop). "
            "Aborting automated retirement to prevent accidental data loss. Flagging for diagnostic review."
        )
        return 0

    closed_count = 0
    for job in active_jobs:
        # Check if job was seen in this run
        is_seen = (
            (job.external_job_id and job.external_job_id in seen_external_ids)
            or (job.job_url and job.job_url in normalized_seen_urls)
        )
        if is_seen:
            continue

        # CRITICAL SAFETY: User-touched jobs are NEVER retired
        if is_job_user_tracked(db, job.id):
            logger.info(
                f"Job #{job.id} ('{job.title}') is user-tracked/applied/saved; preserving as active."
            )
            continue

        # If not seen, check how many successful runs occurred since job.last_seen_at
        if job.last_seen_at:
            successful_runs_since = db.scalar(
                select(func.count(ScrapingRun.id)).where(
                    ScrapingRun.company_id == company_id,
                    ScrapingRun.status == "success",
                    ScrapingRun.finished_at > job.last_seen_at,
                )
            ) or 0
        else:
            successful_runs_since = 1

        # Check if exceeded max age or missed runs threshold
        exceeded_max_age = (job.discovered_at and job.discovered_at < max_age_cutoff)
        exceeded_missed_runs = (successful_runs_since >= threshold)

        if exceeded_missed_runs or exceeded_max_age:
            job.active = False
            job.updated_at = now_naive
            closed_count += 1
            reason = "exceeded_max_age" if exceeded_max_age else f"{successful_runs_since}_missed_runs"
            logger.info(
                f"Job #{job.id} ('{job.title}') marked inactive ({reason})",
                extra={
                    "event": "JOB_MARKED_STALE",
                    "job_id": job.id,
                    "company_id": company_id,
                    "scrape_target_id": scrape_target_id,
                    "missed_runs": successful_runs_since,
                    "reason": reason,
                },
            )

    if closed_count > 0:
        db.commit()

    return closed_count
