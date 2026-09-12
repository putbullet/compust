from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..logging import get_logger
from ..models import ScrapingRun

logger = get_logger("scraper.runs")


def start_scraping_run(db: Session, company_id: int) -> ScrapingRun:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run = ScrapingRun(
        company_id=company_id,
        status="running",
        started_at=now,
        finished_at=None,
        jobs_found=0,
        jobs_added=0,
        jobs_updated=0,
        error_message=None,
    )
    if hasattr(db, "add"):
        db.add(run)
    if hasattr(db, "commit"):
        db.commit()
    if hasattr(db, "refresh"):
        db.refresh(run)
    
    logger.info(
        f"Scraping run #{run.id} started for company {company_id}",
        extra={"event": "RUN_STARTED", "scraping_run_id": run.id, "company_id": company_id},
    )
    return run


def finish_scraping_run(
    db: Session,
    run: ScrapingRun,
    *,
    jobs_found: int = 0,
    jobs_added: int = 0,
    jobs_updated: int = 0,
    parser_errors: list[str] | None = None,
    request_error: str | None = None,
    error_message: str | None = None,
    forced_status: str | None = None,
) -> ScrapingRun:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    run.finished_at = now
    run.jobs_found = jobs_found
    run.jobs_added = jobs_added
    run.jobs_updated = jobs_updated

    # Combine errors for error_message column
    all_errs: list[str] = []
    if error_message:
        all_errs.append(error_message)
    if request_error:
        all_errs.append(f"Request error: {request_error}")
    if parser_errors:
        all_errs.append(f"Parser errors: {'; '.join(parser_errors)}")
    run.error_message = "\n".join(all_errs) if all_errs else None

    if forced_status:
        run.status = forced_status
    elif request_error or (parser_errors and jobs_found == 0):
        run.status = "failed"
    elif parser_errors and jobs_found > 0:
        run.status = "partial"
    else:
        run.status = "success"

    if hasattr(db, "add"):
        db.add(run)
    if hasattr(db, "commit"):
        db.commit()
    if hasattr(db, "refresh"):
        db.refresh(run)

    logger.info(
        f"Scraping run #{run.id} finished with status={run.status} (found={run.jobs_found}, added={run.jobs_added}, updated={run.jobs_updated})",
        extra={
            "event": "RUN_FINISHED",
            "scraping_run_id": run.id,
            "company_id": run.company_id,
            "status": run.status,
            "jobs_found": run.jobs_found,
            "jobs_added": run.jobs_added,
            "jobs_updated": run.jobs_updated,
        },
    )
    return run


def list_scraping_runs_for_company(
    db: Session,
    company_id: int,
    limit: int = 50,
) -> list[ScrapingRun]:
    return list(
        db.scalars(
            select(ScrapingRun)
            .where(ScrapingRun.company_id == company_id)
            .order_by(ScrapingRun.id.desc())
            .limit(limit)
        ).all()
    )


def list_scraping_runs(db: Session, company_id: int, limit: int = 50) -> list[ScrapingRun]:
    return list_scraping_runs_for_company(db, company_id, limit=limit)
