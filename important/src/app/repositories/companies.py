from datetime import datetime, timezone
import logging
from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..models import (
    Company,
    Country,
    ScrapeTarget,
    Job,
    ScrapingRun,
    company_countries,
    JobSkill,
    JobTranslation,
    UserApplication,
    Resume,
    CustomizedResume,
)
from ..services.data_manager import data_manager_service

logger = logging.getLogger("repositories.companies")


def list_companies(db: Session, include_inactive: bool = True) -> list[Company]:
    stmt = select(Company).order_by(Company.name)
    if not include_inactive:
        stmt = stmt.where(Company.active.is_(True))
    return list(db.scalars(stmt).all())


def get_company(db: Session, company_id: int) -> Company | None:
    return db.scalar(select(Company).where(Company.id == company_id))


def create_company(
    db: Session,
    name: str,
    website_url: str,
    careers_url: str | None = None,
    active: bool = True,
    country_ids: list[int] | None = None,
) -> Company:
    company = Company(
        name=name.strip(),
        website_url=website_url.strip(),
        careers_url=careers_url.strip() if careers_url else None,
        active=active,
    )
    if country_ids:
        countries = list(db.scalars(select(Country).where(Country.id.in_(country_ids))).all())
        company.countries = countries

    db.add(company)
    db.commit()
    db.refresh(company)

    if company.careers_url:
        target = ScrapeTarget(
            company_id=company.id,
            url=company.careers_url,
            type="generic_html",
            active=company.active,
            status="pending",
        )
        db.add(target)
        db.commit()

    return company


def update_company(
    db: Session,
    company_id: int,
    name: str | None = None,
    website_url: str | None = None,
    careers_url: str | None = None,
    active: bool | None = None,
    country_ids: list[int] | None = None,
) -> Company | None:
    company = get_company(db, company_id)
    if not company:
        return None

    if name is not None:
        company.name = name.strip()
    if website_url is not None:
        company.website_url = website_url.strip()
    if careers_url is not None:
        company.careers_url = careers_url.strip() if careers_url else None
    if active is not None:
        company.active = active
    if country_ids is not None:
        countries = list(db.scalars(select(Country).where(Country.id.in_(country_ids))).all())
        company.countries = countries

        # Re-evaluate existing jobs under this company based on their location text
        from .countries import resolve_country_by_location
        from ..models import Job
        jobs = list(db.scalars(select(Job).where(Job.company_id == company_id)).all())
        for j in jobs:
            if j.location:
                resolved = resolve_country_by_location(db, j.location)
                if resolved:
                    j.country_id = resolved.id
                elif company.countries and j.country_id not in [c.id for c in company.countries]:
                    j.country_id = company.countries[0].id

    # Synchronize primary scrape target with company careers_url
    if company.careers_url:
        existing_targets = list(db.scalars(select(ScrapeTarget).where(ScrapeTarget.company_id == company.id)).all())
        matching = [t for t in existing_targets if t.url.strip() == company.careers_url]
        if not matching:
            if existing_targets:
                existing_targets[0].url = company.careers_url
                existing_targets[0].active = company.active
            else:
                new_target = ScrapeTarget(
                    company_id=company.id,
                    url=company.careers_url,
                    type="generic_html",
                    active=company.active,
                    status="pending",
                )
                db.add(new_target)
        else:
            for t in matching:
                t.active = company.active

    db.commit()
    db.refresh(company)
    return company


# Re-export scrape_targets functions for backward compatibility
from .scrape_targets import list_scrape_targets, get_scrape_target  # noqa: E402


def toggle_company_active(db: Session, company_id: int) -> Company | None:
    company = get_company(db, company_id)
    if not company:
        return None
    company.active = not company.active
    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company_id: int, hard_delete: bool = False) -> bool:
    company = get_company(db, company_id)
    if not company:
        return False

    if not hard_delete:
        # Safe deactivation
        company.active = False
        db.commit()
        return True

    # Hard deletion: explicitly confirm destruction of company, targets, runs, jobs
    # Delete related jobs first
    db.execute(delete(Job).where(Job.company_id == company_id))
    db.execute(delete(ScrapeTarget).where(ScrapeTarget.company_id == company_id))
    db.execute(delete(ScrapingRun).where(ScrapingRun.company_id == company_id))
    company.countries.clear()
    db.delete(company)
    db.commit()
    return True



def get_or_create_archived_company(db: Session) -> Company:
    """Get or create a designated system company to hold preserved jobs from deleted companies."""
    archived = db.scalar(
        select(Company).where(Company.name == "[Archived Employer]").limit(1)
    )
    if not archived:
        archived = Company(
            name="[Archived Employer]",
            website_url="https://archived.local",
            careers_url="",
            active=False,
        )
        db.add(archived)
        db.flush()
    return archived


def _build_company_scope_query(
    company_ids: list[int] | None = None,
    search: str | None = None,
    filter_active: str | None = None,
):
    stmt = select(Company)
    if company_ids is not None:
        if len(company_ids) == 0:
            return None
        stmt = stmt.where(Company.id.in_(company_ids))
    else:
        if search and search.strip():
            term = f"%{search.strip()}%".lower()
            stmt = stmt.where(
                (Company.name.ilike(term)) | (Company.website_url.ilike(term))
            )
        if filter_active == "active":
            stmt = stmt.where(Company.active.is_(True))
        elif filter_active == "inactive":
            stmt = stmt.where(Company.active.is_(False))
    return stmt


def get_companies_scope_stats(
    db: Session,
    company_ids: list[int] | None = None,
    search: str | None = None,
    filter_active: str | None = None,
) -> dict[str, int]:
    """Calculates company, scrape target, and job protection counts for the current scope."""
    stmt = _build_company_scope_query(company_ids, search, filter_active)
    if stmt is None:
        return {
            "total_companies": 0,
            "total_jobs": 0,
            "untracked_jobs": 0,
            "protected_jobs": 0,
            "scrape_targets_count": 0,
        }

    matched_companies = list(db.scalars(stmt).all())
    total_companies = len(matched_companies)
    if total_companies == 0:
        return {
            "total_companies": 0,
            "total_jobs": 0,
            "untracked_jobs": 0,
            "protected_jobs": 0,
            "scrape_targets_count": 0,
        }

    matched_ids = [c.id for c in matched_companies]

    scrape_targets_count = len(
        list(db.scalars(select(ScrapeTarget.id).where(ScrapeTarget.company_id.in_(matched_ids))).all())
    )

    jobs = list(db.scalars(select(Job.id).where(Job.company_id.in_(matched_ids))).all())
    total_jobs = len(jobs)

    if total_jobs == 0:
        return {
            "total_companies": total_companies,
            "total_jobs": 0,
            "untracked_jobs": 0,
            "protected_jobs": 0,
            "scrape_targets_count": scrape_targets_count,
        }

    job_ids = jobs
    app_job_ids = set(
        db.scalars(
            select(UserApplication.job_id)
            .where(UserApplication.job_id.in_(job_ids))
            .distinct()
        ).all()
    )
    resume_job_ids = set(
        db.scalars(
            select(Resume.target_job_id)
            .where(Resume.target_job_id.in_(job_ids))
            .distinct()
        ).all()
    )
    custom_resume_job_ids = set(
        db.scalars(
            select(CustomizedResume.job_id)
            .where(CustomizedResume.job_id.in_(job_ids))
            .distinct()
        ).all()
    )
    protected_set = (app_job_ids | resume_job_ids | custom_resume_job_ids) - {None}
    protected_jobs = len(protected_set)
    untracked_jobs = max(0, total_jobs - protected_jobs)

    return {
        "total_companies": total_companies,
        "total_jobs": total_jobs,
        "untracked_jobs": untracked_jobs,
        "protected_jobs": protected_jobs,
        "scrape_targets_count": scrape_targets_count,
    }


def delete_all_companies_safely(
    db: Session,
    company_ids: list[int] | None = None,
    search: str | None = None,
    filter_active: str | None = None,
    delete_untracked_jobs: bool = False,
) -> tuple[int, int, int, int, int, str | None]:
    """
    Safely delete all companies/sources in the current view scope.
    1. Triggers an automatic full database backup before applying changes.
    2. Identifies all protected jobs (linked to user applications, notes, or resumes) and NEVER deletes them.
    3. Untracked jobs are deleted only if delete_untracked_jobs is True; otherwise detached/archived.
    4. Detaches protected/kept jobs to a system archived employer record.
    5. Deletes targets, runs, country links, and companies.
    Returns (deleted_companies_count, deleted_targets_count, deleted_jobs_count, preserved_jobs_count, total_companies_matched, backup_filename).
    """
    # 1. Automatic pre-deletion database backup
    backup_filename = None
    try:
        backup_res = data_manager_service.export_backup()
        backup_filename = backup_res.filename
        logger.info(f"Pre-deletion backup successfully created: {backup_filename}")
    except Exception as e:
        logger.error(f"Automatic pre-deletion backup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Automatic pre-deletion backup failed ({str(e)}). Deletion aborted for safety.",
        )

    # 2. Scope resolution
    stmt = _build_company_scope_query(company_ids, search, filter_active)
    if stmt is None:
        return 0, 0, 0, 0, 0, backup_filename

    matched_companies = list(db.scalars(stmt).all())
    total_companies_matched = len(matched_companies)
    if total_companies_matched == 0:
        return 0, 0, 0, 0, 0, backup_filename

    matched_company_ids = [c.id for c in matched_companies]
    company_name_map = {c.id: c.name for c in matched_companies}

    # 3. Identify all jobs linked to these companies
    jobs = list(db.scalars(select(Job).where(Job.company_id.in_(matched_company_ids))).all())
    job_ids = [j.id for j in jobs]

    # 4. Check for protected jobs (applications, resumes, customized resumes)
    protected_job_ids = set()
    if job_ids:
        app_job_ids = set(
            db.scalars(
                select(UserApplication.job_id)
                .where(UserApplication.job_id.in_(job_ids))
                .distinct()
            ).all()
        )
        resume_job_ids = set(
            db.scalars(
                select(Resume.target_job_id)
                .where(Resume.target_job_id.in_(job_ids))
                .distinct()
            ).all()
        )
        custom_resume_job_ids = set(
            db.scalars(
                select(CustomizedResume.job_id)
                .where(CustomizedResume.job_id.in_(job_ids))
                .distinct()
            ).all()
        )
        protected_job_ids = (app_job_ids | resume_job_ids | custom_resume_job_ids) - {None}

        # Backfill custom_company_name on user applications if not already set
        if app_job_ids:
            for j in jobs:
                if j.id in app_job_ids:
                    apps = list(db.scalars(select(UserApplication).where(UserApplication.job_id == j.id)).all())
                    for app in apps:
                        if not app.custom_company_name:
                            app.custom_company_name = company_name_map.get(j.company_id, "Company")

    # 5. Partition jobs into untracked vs preserved
    deleted_jobs_count = 0
    preserved_jobs_count = 0

    untracked_jobs = [j for j in jobs if j.id not in protected_job_ids]
    jobs_to_preserve = [j for j in jobs if j.id in protected_job_ids]

    if delete_untracked_jobs:
        untracked_job_ids = [j.id for j in untracked_jobs]
        if untracked_job_ids:
            db.execute(delete(JobSkill).where(JobSkill.job_id.in_(untracked_job_ids)))
            db.execute(delete(JobTranslation).where(JobTranslation.job_id.in_(untracked_job_ids)))
            db.execute(delete(Job).where(Job.id.in_(untracked_job_ids)))
            deleted_jobs_count = len(untracked_job_ids)
    else:
        jobs_to_preserve.extend(untracked_jobs)

    # 6. Detach preserved jobs to archived company and deactivate
    if jobs_to_preserve:
        archived_company = get_or_create_archived_company(db)
        preserve_ids = [j.id for j in jobs_to_preserve]
        db.execute(
            update(Job)
            .where(Job.id.in_(preserve_ids))
            .values(company_id=archived_company.id, scrape_target_id=None, active=False)
        )
        preserved_jobs_count = len(preserve_ids)

    # 7. Scrape targets and runs cleanup
    # Clear any foreign key on remaining jobs if they point to scrape targets being deleted
    db.execute(
        update(Job)
        .where(Job.company_id.in_(matched_company_ids))
        .values(scrape_target_id=None)
    )

    target_ids = list(
        db.scalars(
            select(ScrapeTarget.id).where(ScrapeTarget.company_id.in_(matched_company_ids))
        ).all()
    )
    deleted_targets_count = len(target_ids)

    # Delete scraping runs
    db.execute(delete(ScrapingRun).where(ScrapingRun.company_id.in_(matched_company_ids)))
    if target_ids:
        db.execute(delete(ScrapeTarget).where(ScrapeTarget.id.in_(target_ids)))

    # Clear country associations
    db.execute(
        delete(company_countries).where(company_countries.c.company_id.in_(matched_company_ids))
    )

    # 8. Delete companies (excluding archived company)
    archived_id = get_or_create_archived_company(db).id
    final_delete_company_ids = [cid for cid in matched_company_ids if cid != archived_id]

    if final_delete_company_ids:
        db.execute(delete(Company).where(Company.id.in_(final_delete_company_ids)))

    db.commit()
    deleted_companies_count = len(final_delete_company_ids)

    return (
        deleted_companies_count,
        deleted_targets_count,
        deleted_jobs_count,
        preserved_jobs_count,
        total_companies_matched,
        backup_filename,
    )
