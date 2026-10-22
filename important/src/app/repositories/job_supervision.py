from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from ..models import Job, JobSkill, UserApplication, JobTranslation


def update_job_supervision(
    db: Session,
    job_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    location: str | None = None,
    department: str | None = None,
    employment_type: str | None = None,
    remote_type: str | None = None,
    job_url: str | None = None,
    active: bool | None = None,
) -> Job | None:
    """Allow user to manually correct scraper errors on a job record."""
    job = db.scalar(select(Job).where(Job.id == job_id))
    if not job:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if title is not None:
        job.title = title.strip()
    if description is not None:
        job.description = description.strip()
    if location is not None:
        job.location = location.strip() if location else None
    if department is not None:
        job.department = department.strip() if department else None
    if employment_type is not None:
        job.employment_type = employment_type.strip() if employment_type else None
    if remote_type is not None:
        job.remote_type = remote_type.strip() if remote_type else None
    if job_url is not None:
        job.job_url = job_url.strip()
    if active is not None:
        job.active = active

    job.updated_at = now
    db.commit()
    db.refresh(job)
    return job


def toggle_job_active(db: Session, job_id: int) -> Job | None:
    """Soft deactivate / hide a bad job without destroying history."""
    job = db.scalar(select(Job).where(Job.id == job_id))
    if not job:
        return None
    job.active = not job.active
    job.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(job)
    return job


def delete_job_safely(db: Session, job_id: int, force: bool = False) -> bool:
    """
    Safely delete an erroneous job candidate.
    If the job has user applications, soft-deactivates unless force is True.
    """
    job = db.scalar(select(Job).where(Job.id == job_id))
    if not job:
        return False

    has_apps = db.scalar(select(UserApplication.id).where(UserApplication.job_id == job_id).limit(1))
    if has_apps and not force:
        # Soft deactivate to preserve user application history
        job.active = False
        db.commit()
        return True

    # Delete skills and translations
    db.execute(delete(JobSkill).where(JobSkill.job_id == job_id))
    db.execute(delete(JobTranslation).where(JobTranslation.job_id == job_id))
    if force and has_apps:
        db.execute(delete(UserApplication).where(UserApplication.job_id == job_id))

    db.delete(job)
    db.commit()
    return True


def bulk_delete_jobs_safely(db: Session, job_ids: list[int], force: bool = False) -> tuple[int, int]:
    """
    Safely delete multiple job candidates in batch.
    Returns (deleted_count, deactivated_count).
    """
    if not job_ids:
        return 0, 0

    deleted_count = 0
    deactivated_count = 0
    for job_id in job_ids:
        job = db.scalar(select(Job).where(Job.id == job_id))
        if not job:
            continue

        has_apps = db.scalar(select(UserApplication.id).where(UserApplication.job_id == job_id).limit(1))
        if has_apps and not force:
            job.active = False
            deactivated_count += 1
        else:
            db.execute(delete(JobSkill).where(JobSkill.job_id == job_id))
            db.execute(delete(JobTranslation).where(JobTranslation.job_id == job_id))
            if force and has_apps:
                db.execute(delete(UserApplication).where(UserApplication.job_id == job_id))
            db.delete(job)
            deleted_count += 1

    db.commit()
    return deleted_count, deactivated_count


def delete_all_jobs_safely(
    db: Session,
    search: str | None = None,
    force_tracked: bool = False,
    batch_size: int = 100,
) -> tuple[int, int, int]:
    """
    Safely delete all jobs in the database (or matching search filter).
    Protects user-tracked jobs / applications by default unless force_tracked is explicitly True.
    Returns (deleted_count, preserved_tracked_count, total_matched).
    """
    query = select(Job)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            (Job.title.ilike(term))
            | (Job.description.ilike(term))
            | (Job.location.ilike(term))
            | (Job.department.ilike(term))
        )

    matched_jobs = db.scalars(query).all()
    total_matched = len(matched_jobs)
    if total_matched == 0:
        return 0, 0, 0

    deleted_count = 0
    preserved_tracked_count = 0

    for i, job in enumerate(matched_jobs):
        has_apps = db.scalar(
            select(UserApplication.id).where(UserApplication.job_id == job.id).limit(1)
        )
        if has_apps and not force_tracked:
            # Preserve user application history
            job.active = False
            preserved_tracked_count += 1
        else:
            db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
            db.execute(delete(JobTranslation).where(JobTranslation.job_id == job.id))
            if force_tracked and has_apps:
                db.execute(delete(UserApplication).where(UserApplication.job_id == job.id))
            db.delete(job)
            deleted_count += 1

        if (i + 1) % batch_size == 0:
            db.commit()

    db.commit()
    return deleted_count, preserved_tracked_count, total_matched

