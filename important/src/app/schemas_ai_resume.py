from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class AIChatRequest(BaseModel):
    query: str
    model: str | None = None


class AIChatResponse(BaseModel):
    answer: str
    facts: dict[str, Any]
    provider: str
    model: str | None = None
    ollama_available: bool = False


class AIModelRead(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None
    parameter_size: str | None = None
    quantization_level: str | None = None


class AIStatusResponse(BaseModel):
    provider: str
    url: str
    status: str
    models: list[AIModelRead]
    selected_model: str | None = None
    selected_model_available: bool = False
    error: str | None = None


class AIProviderRead(BaseModel):
    id: str
    name: str
    status: str
    enabled: bool
    is_local: bool
    endpoint: str | None = None
    models_count: int = 0


class AISettingsUpdate(BaseModel):
    selected_model: str


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    filename: str
    parsed_sections: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResumeSuggestionResponse(BaseModel):
    job_id: int
    job_title: str
    already_demonstrated: list[str]
    missing_or_weak: list[str]
    ats_improvements: list[str] = []
    actionable_recommendations: list[dict[str, Any]] = []
    suggestions: list[str]
    requirements_status: str
    ai_enhanced: bool = False
    provider: str = "deterministic"


class CustomizedResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    base_resume_id: int
    job_id: int
    version: int
    pdf_filename: str | None = None
    docx_filename: str | None = None
    ats_analysis: dict[str, Any] | None = None
    recommendations: list[dict[str, Any]] | None = None
    created_at: datetime


class JobSupervisionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    department: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    job_url: str | None = None
    active: bool | None = None


class BulkJobDeleteRequest(BaseModel):
    job_ids: list[int]
    force: bool = False


class BulkJobDeleteResponse(BaseModel):
    status: str
    deleted_count: int
    deactivated_count: int
    total_requested: int


class ScraperDiagnosticRequest(BaseModel):
    url: str
    strategy: str | None = None
    max_pages: int = 1


class ScraperDiagnosticResponse(BaseModel):
    target_url: str
    strategy_used: str
    platform_detected: str | None = None
    execution_time_seconds: float
    jobs_discovered: int
    jobs_accepted: int
    jobs_rejected: int
    confidence_score: float
    status: str
    errors: list[str] = []
    sample_jobs: list[dict[str, Any]] = []
    http_status: int | None = None
    content_type: str | None = None
    rendering_mode: str | None = None
    discovery_method: str | None = None
    failure_reason: str | None = None
    browser_rendered: bool = False
