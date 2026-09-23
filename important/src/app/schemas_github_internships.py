from typing import Literal
from pydantic import BaseModel, Field

VisaStatusType = Literal[
    "sponsors_visa",
    "no_sponsorship",
    "us_citizen_only",
    "canada_authorized",
    "not_specified",
    "closed",
]


class GitHubInternshipItem(BaseModel):
    id: str
    company: str
    company_domain: str | None = None
    logo_url: str | None = None
    role: str
    location: str
    country: str | None = None
    category: str = "Software Engineering"
    season: str = "Summer 2027"
    source_repo_id: str
    source_repo_name: str
    source_repo_url: str
    apply_url: str
    date_posted: str | None = None
    visa_status: VisaStatusType = "not_specified"
    visa_text: str = "Not Specified"
    is_closed: bool = False
    notes: str | None = None


class GitHubRepoMeta(BaseModel):
    id: str
    name: str
    url: str
    raw_url: str
    region: str
    year: str
    description: str
    item_count: int = 0


class GitHubInternshipStats(BaseModel):
    total_listings: int = 0
    active_listings: int = 0
    closed_listings: int = 0
    visa_sponsored_count: int = 0
    no_sponsorship_count: int = 0
    us_citizens_count: int = 0
    canada_authorized_count: int = 0
    not_specified_count: int = 0
    repos_count: int = 0
    last_synced_at: str | None = None
    by_repo: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)


class GitHubInternshipsResponse(BaseModel):
    items: list[GitHubInternshipItem] = Field(default_factory=list)
    stats: GitHubInternshipStats
    repositories: list[GitHubRepoMeta] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
