from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    job_url: str
    external_job_id: str
    location: str | None
    description: str | None
    employment_type: str | None
    remote_type: str | None
    department: str | None
    posted_at: datetime | None
    skills: list[str]
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None


class ParseResultRead(BaseModel):
    jobs: list[JobCandidateRead]
    errors: list[str]


class JobSyncRead(BaseModel):
    jobs_found: int
    jobs_added: int
    jobs_updated: int
    parser_errors: list[str]
