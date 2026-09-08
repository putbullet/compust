from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import Job, JobSkill
from ..scraper.orange_parser import JobCandidate


def persist_candidates(
    db: Session,
    *,
    company_id: int,
    country_id: int,
    source: str,
    candidates: list[JobCandidate],
) -> tuple[int, int]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    added = 0
    updated = 0
    for candidate in candidates:
        job = db.scalar(
            select(Job).where(
                Job.company_id == company_id,
                Job.external_job_id == candidate.external_job_id,
            )
        )
        if job is None:
            job = db.scalar(
                select(Job).where(
                    Job.company_id == company_id,
                    Job.job_url == candidate.job_url,
                )
            )
        if job is None:
            job = Job(
                company_id=company_id,
                country_id=country_id,
                title=candidate.title,
                location=candidate.location,
                job_url=candidate.job_url,
                description=candidate.description,
                employment_type=candidate.employment_type,
                remote_type=candidate.remote_type,
                department=candidate.department,
                source=source,
                external_job_id=candidate.external_job_id,
                posted_at=candidate.posted_at.replace(tzinfo=None) if candidate.posted_at else None,
                discovered_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
                active=True,
            )
            db.add(job)
            db.flush()
            added += 1
        else:
            updated += 1
        job.country_id = country_id
        job.title = candidate.title
        job.location = candidate.location
        job.job_url = candidate.job_url
        job.description = candidate.description
        job.employment_type = candidate.employment_type
        job.remote_type = candidate.remote_type
        job.department = candidate.department
        job.source = source
        job.external_job_id = candidate.external_job_id
        job.posted_at = candidate.posted_at.replace(tzinfo=None) if candidate.posted_at else None
        job.last_seen_at = now
        job.active = True
        job.updated_at = now
        db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
        db.add_all(
            [
                JobSkill(job_id=job.id, skill=skill)
                for skill in dict.fromkeys(candidate.skills)
            ]
        )
    db.commit()
    return added, updated
