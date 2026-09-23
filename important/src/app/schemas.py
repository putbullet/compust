from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    website_url: str
    careers_url: str | None
    active: bool
    countries: list[CountryRead]


class CompanyCreate(BaseModel):
    name: str
    website_url: str
    careers_url: str | None = None
    active: bool = True
    country_ids: list[int] = []


class CompanyUpdate(BaseModel):
    name: str | None = None
    website_url: str | None = None
    careers_url: str | None = None
    active: bool | None = None
    country_ids: list[int] | None = None


class ScrapeTargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    url: str
    type: str | None
    active: bool
    last_scraped_at: datetime | None
    status: str | None
    cooldown_until: datetime | None = None
    robots_txt_allowed: bool | None = None
    robots_txt_checked_at: datetime | None = None


class ScrapeTargetCreate(BaseModel):
    company_id: int
    url: str
    type: str | None = "generic_html"
    active: bool = True


class ScrapeTargetUpdate(BaseModel):
    url: str | None = None
    type: str | None = None
    active: bool | None = None


class CompanyDetailRead(CompanyRead):
    scrape_targets: list[ScrapeTargetRead] = []
    last_scrape_status: str | None = None
    last_scrape_at: datetime | None = None


class ScrapingRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    jobs_found: int
    jobs_added: int
    jobs_updated: int
    error_message: str | None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    country_id: int
    title: str
    location: str | None
    job_url: str
    employment_type: str | None
    remote_type: str | None
    department: str | None
    source: str | None
    external_job_id: str | None
    posted_at: datetime | None
    discovered_at: datetime
    last_seen_at: datetime | None
    active: bool
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    match_score: int | None = None
    company_name: str | None = None
    country_name: str | None = None
    resume_suggestions: Any | None = None


class JobDetailRead(JobRead):
    description: str | None = None
    skills: list[str] = []
    positive_factors: list[str] = []
    missing_factors: list[str] = []
    category_scores: dict[str, int] = {}


class JobTranslationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    language: str
    title: str
    description: str | None = None
    source_language: str
    created_at: datetime
    updated_at: datetime


class JobTranslationCreate(BaseModel):
    language: str
    title: str | None = None
    description: str | None = None
    source_language: str = "auto"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email_verified: bool
    is_active: bool
    created_at: datetime


class UserPreferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    preferred_job_type: str | None = None
    preferred_work_mode: str | None = None
    preferred_location: str | None = None
    min_salary: float | None = None
    max_salary: float | None = None
    salary_currency: str | None = None


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int
    pages: int


class SourceInspectionRead(BaseModel):
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    fetched_at: str
    title: str | None
    links_count: int
    forms_count: int
    pagination_urls: list[str]
    has_next_link: bool
    structured_data_blocks: int
    api_hints: list[str]


class HealthRead(BaseModel):
    status: str
    database: str
    latency_ms: float | None = None


class JobQuickAddRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    company: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=1000)
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    source: str = "extension:generic"
    resume_suggestions: Any | None = None
    application_status: str | None = None  # None | "saved" | "applied"
    notes: str | None = None


class JobQuickAddResponse(BaseModel):
    job_id: int
    title: str
    company: str
    location: str | None = None
    url: str
    dedup_status: str  # "created" | "existing"
    is_duplicate: bool
    resume_suggestions: Any | None = None
    application_id: int | None = None
    application_status: str | None = None


class JobQuickAddAndAnalyzeResponse(BaseModel):
    job: JobQuickAddResponse
    dedup_status: str
    is_duplicate: bool
    has_active_resume: bool
    message: str | None = None
    match_analysis: dict[str, Any] | None = None
    score_breakdown: dict[str, Any] | None = None


class JobEphemeralAnalyzeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    company: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=1000)
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    source: str = "extension"


class JobEphemeralAnalyzeResponse(BaseModel):
    title: str
    company: str
    location: str | None = None
    url: str
    has_active_resume: bool
    message: str | None = None
    match_score: int | None = None
    positive_factors: list[str] = Field(default_factory=list)
    missing_factors: list[str] = Field(default_factory=list)
    demonstrated_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    resume_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    visa_analysis: dict[str, Any] | None = None
    content_hash: str


class GenericExtractRequest(BaseModel):
    html: str = Field(..., min_length=10)
    url: str = Field(..., min_length=1)


class GenericExtractResponse(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    confidence: str  # "high" | "medium" | "low"
    normalized_title: str | None = None
    message: str | None = None

