from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PortalClassification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    portal_type: str = Field(
        ...,
        description="Guessed portal architecture: workday, smartrecruiters, greenhouse, taleo, turbostream_html, json_api, server_rendered_html, or unknown",
    )
    pagination_style: str = Field(
        ...,
        description="Guessed pagination pattern: rel_next, page_param, offset_limit, show_more_button, single_page, or unknown",
    )
    api_endpoints_detected: list[str] = Field(default_factory=list)
    robots_txt_allowed: bool = Field(default=True)
    robots_txt_checked_at: datetime | None = None
    recommendation: str = Field(...)
    suggested_strategy_type: str = Field(...)


class CompanyOnboardRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Company name")
    website_url: str = Field(..., description="Corporate website URL")
    careers_url: str = Field(..., description="Career portal / vacancies URL")
    country_code: str = Field(default="MA", min_length=2, max_length=2, description="2-letter ISO country code")
    scrape_target_url: str | None = Field(
        default=None,
        description="Specific target URL to scrape (defaults to careers_url if omitted)",
    )
    scrape_interval_hours: int = Field(default=24, ge=1, le=168)


class CompanyOnboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    company_name: str
    country_code: str
    scrape_target_id: int
    scrape_target_url: str
    scrape_target_status: str
    classification: PortalClassification
