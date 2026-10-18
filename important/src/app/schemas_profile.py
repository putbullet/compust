from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from src.app.schemas import UserPreferenceRead, UserRead

ExperienceType = Literal["professional", "internship", "project", "transferable"]
LanguageProficiency = Literal["native", "fluent", "intermediate", "basic"]


class UserExperienceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    experience_type: ExperienceType = "professional"
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class UserExperienceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    company_name: str
    experience_type: str | None = "professional"
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class UserEducationCreate(BaseModel):
    institution: str = Field(..., min_length=1, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class UserEducationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class UserLanguageCreate(BaseModel):
    language: str = Field(..., min_length=1, max_length=100)
    proficiency: LanguageProficiency = "fluent"


class UserLanguageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    language: str
    proficiency: str | None = "fluent"


class UserProfileFullRead(BaseModel):
    user: UserRead
    preferences: UserPreferenceRead | None = None
    skills: list[str] = []
    experience: list[UserExperienceRead] = []
    education: list[UserEducationRead] = []
    languages: list[UserLanguageRead] = []


class LinkedInUrlUpdateRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=500)


class LinkedInProfileStatusResponse(BaseModel):
    linkedin_url: str | None = None
    handle: str | None = None
    status: str  # "not_imported" | "imported" | "needs_refresh"
    import_source: str | None = None
    imported_at: str | None = None
    days_since_import: int | None = None
    extracted_counts: dict[str, int] = Field(default_factory=dict)


class UnifiedProfileResponse(BaseModel):
    version_hash: str
    use_linkedin_in_matching: bool
    updated_at: str
    contact: dict = Field(default_factory=dict)
    skills: list = Field(default_factory=list)
    experience: list = Field(default_factory=list)
    education: list = Field(default_factory=list)
    certifications: list = Field(default_factory=list)
    languages: list = Field(default_factory=list)
    projects: list = Field(default_factory=list)
    honors: list = Field(default_factory=list)
    courses: list = Field(default_factory=list)
    conflicts: list = Field(default_factory=list)
    user_overrides: dict = Field(default_factory=dict)


class UnifiedProfileOverridesRequest(BaseModel):
    pinned_skills: list[str] = Field(default_factory=list)
    hidden_skills: list[str] = Field(default_factory=list)


class UnifiedToggleMatchingRequest(BaseModel):
    enabled: bool

