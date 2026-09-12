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
