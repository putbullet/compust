from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Job, ScrapingRun
from ..logging import get_logger
from ..scraper.url_normalizer import normalize_url

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


def evaluate_target_stale_jobs(
    db: Session,
    *,
    company_id: int,
    scrape_target_id: int,
    seen_external_ids: set[str],
    seen_urls: set[str],
    is_full_success: bool,
    max_missed_runs: int | None = None,
) -> int:
    """
    Cautiously evaluates active jobs for a scrape target and marks them inactive
    ONLY if the source scrape was 100% successful and the job was absent across
    multiple consecutive verified successful crawl runs.
    """
    if not is_full_success:
        logger.info(
            f"Skipping stale evaluation for target {scrape_target_id}: scrape was partial or failed."
        )
        return 0

    settings = get_settings()
    threshold = max_missed_runs if max_missed_runs is not None else settings.stale_job_missed_runs_threshold

    now = datetime.now(timezone.utc).replace(tzinfo=None)

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

    closed_count = 0
    for job in active_jobs:
        # Check if job was seen in this run
        is_seen = (
            (job.external_job_id and job.external_job_id in seen_external_ids)
            or (job.job_url and job.job_url in normalized_seen_urls)
        )
        if is_seen:
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

        # Only mark inactive if missed across multiple consecutive verified runs
        if successful_runs_since >= threshold:
            job.active = False
            job.updated_at = now
            closed_count += 1
            logger.info(
                f"Job #{job.id} ('{job.title}') marked inactive after {successful_runs_since} missed successful runs",
                extra={
                    "event": "JOB_MARKED_STALE",
                    "job_id": job.id,
                    "company_id": company_id,
                    "scrape_target_id": scrape_target_id,
                    "missed_runs": successful_runs_since,
                },
            )

    if closed_count > 0:
        db.commit()

    return closed_count
