from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, computed_field

from .schemas import JobRead

ApplicationStatus = Literal[
    "saved",
    "applied",
    "no_answer",
    "interviewing",
    "1st_interview",
    "2nd_interview",
    "3rd_interview",
    "final_interview",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
]


class ApplicationCreate(BaseModel):
    """Payload when saving or marking a Compust job as applied."""
    status: str = "saved"
    notes: str | None = None
    source: str = "Compust"


class ManualApplicationCreate(BaseModel):
    """Payload for user-created external applications (LinkedIn, Indeed, etc.)."""
    job_title: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    source: str = "LinkedIn"
    status: str = "applied"
    location: str | None = None
    country: str | None = None
    job_url: str | None = None
    applied_at: datetime | None = None
    salary: str | None = None
    employment_type: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    recruiter: str | None = None
    referral: str | None = None
    priority: str = "medium"
    notes: str | None = None
    next_follow_up: date | None = None
    interview_date: datetime | None = None


class ApplicationUpdate(BaseModel):
    """Payload for modifying an existing tracked application row."""
    status: str | None = None
    notes: str | None = None
    applied_at: datetime | None = None
    job_title: str | None = None
    company_name: str | None = None
    location: str | None = None
    country: str | None = None
    job_url: str | None = None
    source: str | None = None
    salary: str | None = None
    employment_type: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    recruiter: str | None = None
    referral: str | None = None
    priority: str | None = None
    next_follow_up: date | None = None
    interview_date: datetime | None = None


class ApplicationHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    from_status: str | None = None
    to_status: str
    changed_at: datetime
    notes: str | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_id: int | None = None
    status: str
    notes: str | None = None
    applied_at: datetime | None = None
    source: str = "Compust"

    # Custom fields for manual apps or row-level overrides
    custom_job_title: str | None = None
    custom_company_name: str | None = None
    custom_location: str | None = None
    custom_country: str | None = None
    custom_job_url: str | None = None
    salary: str | None = None
    employment_type: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    recruiter: str | None = None
    referral: str | None = None
    priority: str = "medium"
    next_follow_up: date | None = None
    interview_date: datetime | None = None

    created_at: datetime
    updated_at: datetime
    job: JobRead | None = None
    history: list[ApplicationHistoryRead] = []

    @computed_field
    @property
    def effective_title(self) -> str:
        if self.custom_job_title:
            return self.custom_job_title
        if self.job and self.job.title:
            return self.job.title
        return f"Application #{self.id}"

    @computed_field
    @property
    def effective_company(self) -> str:
        if self.custom_company_name:
            return self.custom_company_name
        if self.job and self.job.company_name:
            return self.job.company_name
        return "Company"

    @computed_field
    @property
    def effective_location(self) -> str | None:
        if self.custom_location:
            return self.custom_location
        if self.job:
            return self.job.location
        return None

    @computed_field
    @property
    def effective_country(self) -> str | None:
        if self.custom_country:
            return self.custom_country
        if self.job and self.job.country_name:
            return self.job.country_name
        return None

    @computed_field
    @property
    def effective_job_url(self) -> str | None:
        if self.custom_job_url:
            return self.custom_job_url
        if self.job:
            return self.job.job_url
        return None


class ApplicationStatsRead(BaseModel):
    total_applications: int
    active_applications: int
    status_breakdown: dict[str, int]
    source_breakdown: dict[str, int]
    interview_rate_percent: float
    response_rate_percent: float
    offer_rate_percent: float
    acceptance_rate_percent: float
    rejection_rate_percent: float
    avg_days_to_interview: float | None = None
    avg_days_to_offer: float | None = None


class SankeyNode(BaseModel):
    id: str
    label: str
    stage_index: int
    count: int
    color: str


class SankeyLink(BaseModel):
    source: str
    target: str
    value: int


class SankeyDataRead(BaseModel):
    nodes: list[SankeyNode]
    links: list[SankeyLink]
    total: int
