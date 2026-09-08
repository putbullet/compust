from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class ScrapeTargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    url: str
    type: str | None
    active: bool
    last_scraped_at: datetime | None
    status: str | None


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
