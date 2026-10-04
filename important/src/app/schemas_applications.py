from datetime import date, datetime
from typing import Any, Literal
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
    resume_suggestions: Any | None = None


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
    contact_id: int | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    recruiter: str | None = None
    referral: str | None = None
    priority: str = "medium"
    notes: str | None = None
    next_follow_up: date | None = None
    interview_date: datetime | None = None
    resume_suggestions: Any | None = None


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
    contact_id: int | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    recruiter: str | None = None
    referral: str | None = None
    priority: str | None = None
    next_follow_up: date | None = None
    interview_date: datetime | None = None
    resume_suggestions: Any | None = None


class ApplicationEventCreate(BaseModel):
    """Payload for logging a meaningful event or note on an application's timeline."""
    event_type: str = "note"
    event_title: str = Field(..., min_length=1)
    notes: str | None = None
    event_date: datetime | None = None


class FollowUpActionPayload(BaseModel):
    """Quick action payload for follow-ups (complete, snooze, reschedule, cancel)."""
    action: Literal["complete", "snooze", "reschedule", "cancel"]
    days: int | None = None  # e.g., 2, 7 for snooze
    new_date: date | None = None  # for reschedule
    notes: str | None = None


class ApplicationHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    from_status: str | None = None
    to_status: str
    changed_at: datetime
    notes: str | None = None
    event_type: str = "status_change"
    event_title: str | None = None


# ---------------------------------------------------------------------------
# Contact & Interaction schemas
# ---------------------------------------------------------------------------

class ContactInteractionCreate(BaseModel):
    type: str = "email_sent"  # email_sent, email_received, linkedin_message, phone_call, meeting, interview, follow_up, note, other
    summary: str = Field(..., min_length=1)
    details: str | None = None
    interaction_date: datetime | None = None
    application_id: int | None = None


class ContactInteractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    application_id: int | None = None
    user_id: int
    type: str
    summary: str
    details: str | None = None
    interaction_date: datetime
    created_at: datetime


class RelatedApplicationSummary(BaseModel):
    id: int
    job_title: str
    company_name: str
    status: str
    applied_at: datetime | None = None
    source: str = "Compust"


class ContactCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    name: str = Field(..., min_length=1)
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    linkedin_url: str | None = None
    location: str | None = None
    notes: str | None = None
    tags: str | None = None
    application_id: int | None = None  # Optional application to immediately link to

    # Communication & Interaction fields (Distinguish identity from interaction)
    contacted: bool | None = None
    contact_method: str | None = None  # email, linkedin, phone, other
    contact_date: datetime | None = None
    email_used: str | None = None
    response_received: bool | None = None
    response_date: datetime | None = None
    response_notes: str | None = None


class ContactUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    linkedin_url: str | None = None
    location: str | None = None
    notes: str | None = None
    tags: str | None = None

    # Communication & Interaction update fields
    contacted: bool | None = None
    contact_method: str | None = None
    contact_date: datetime | None = None
    email_used: str | None = None
    response_received: bool | None = None
    response_date: datetime | None = None
    response_notes: str | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    linkedin_url: str | None = None
    location: str | None = None
    notes: str | None = None
    tags: str | None = None
    created_at: datetime
    updated_at: datetime

    # Factual insights derived from actual applications data
    applications_count: int = 0
    responses_count: int = 0
    interviews_count: int = 0
    last_interaction_date: datetime | None = None
    last_contacted_at: datetime | None = None
    last_response_at: datetime | None = None
    has_responded: bool = False
    next_action: str | None = None

    # Distinct communication state: 'not_contacted' | 'contacted_no_response' | 'responded'
    communication_status: str = "not_contacted"
    preferred_contact_method: str | None = None
    email_used: str | None = None

    interactions: list[ContactInteractionRead] = []
    related_applications: list[RelatedApplicationSummary] = []


class ContactDuplicateMatch(BaseModel):
    contact: ContactRead
    match_reason: str
    confidence: Literal["exact", "high", "medium"]


class ContactImportPreviewRow(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    linkedin_url: str | None = None
    location: str | None = None
    notes: str | None = None
    tags: str | None = None
    status: Literal["new", "existing", "duplicate"] = "new"
    match_id: int | None = None
    match_name: str | None = None


class ContactImportPreviewResult(BaseModel):
    total_detected: int
    new_count: int
    existing_count: int
    duplicate_count: int
    column_mapping: dict[str, str]
    preview_rows: list[ContactImportPreviewRow]


class ContactImportConfirmPayload(BaseModel):
    mode: Literal["skip_duplicates", "update_existing", "import_all"] = "skip_duplicates"
    rows: list[ContactImportPreviewRow]


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
    contact_id: int | None = None
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
    resume_suggestions: Any | None = None
    job: JobRead | None = None
    contact: ContactRead | None = None
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


class SourceAnalyticsItem(BaseModel):
    source: str
    applications: int
    responses: int
    interviews: int
    offers: int
    response_rate_percent: float
    interview_rate_percent: float


class ActivityTimePoint(BaseModel):
    date: str
    applications: int
    responses: int
    interviews: int
    offers: int


class SearchOverview(BaseModel):
    total_applications: int
    applications_this_week: int
    total_responses: int
    total_interviews: int
    total_offers: int
    avg_response_time_days: float | None = None
    upcoming_interviews: int = 0
    upcoming_follow_ups: int = 0
    overdue_follow_ups: int = 0


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

    # Advanced Upgrade analytics (derived directly from real user data)
    source_analytics: list[SourceAnalyticsItem] = Field(default_factory=list)
    activity_timeline: dict[str, list[ActivityTimePoint]] = Field(default_factory=dict)
    overview: SearchOverview | None = None


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
