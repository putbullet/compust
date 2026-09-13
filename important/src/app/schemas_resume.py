from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ResumeProfileSchema(BaseModel):
    full_name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    website: str = ""
    github: str = ""
    linkedin: str = ""
    summary: str = ""


class ResumeExperienceItem(BaseModel):
    id: str
    company: str = ""
    title: str = ""
    location: str = ""
    employment_type: str = "full_time"
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    description: str = ""
    highlights: list[str] = Field(default_factory=list)


class ResumeEducationItem(BaseModel):
    id: str
    institution: str = ""
    degree: str = ""
    field: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    description: str = ""


class ResumeSkillItem(BaseModel):
    id: str
    name: str = ""
    category: str = "Technical"
    proficiency: str = "Intermediate"


class ResumeProjectItem(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    technologies: str = ""
    url: str = ""
    start_date: str = ""
    end_date: str = ""


class ResumeCertificationItem(BaseModel):
    id: str
    name: str = ""
    issuer: str = ""
    issue_date: str = ""
    expiration_date: str = ""
    url: str = ""


class ResumeLanguageItem(BaseModel):
    id: str
    language: str = ""
    proficiency: str = "Fluent"


class ResumeCustomSectionItem(BaseModel):
    id: str
    title: str = ""
    items: list[str] = Field(default_factory=list)


class StructuredResumeData(BaseModel):
    profile: ResumeProfileSchema = Field(default_factory=ResumeProfileSchema)
    experience: list[ResumeExperienceItem] = Field(default_factory=list)
    education: list[ResumeEducationItem] = Field(default_factory=list)
    skills: list[ResumeSkillItem] = Field(default_factory=list)
    projects: list[ResumeProjectItem] = Field(default_factory=list)
    certifications: list[ResumeCertificationItem] = Field(default_factory=list)
    languages: list[ResumeLanguageItem] = Field(default_factory=list)
    custom_sections: list[ResumeCustomSectionItem] = Field(default_factory=list)


ResumeTemplateType = Literal["modern", "classic", "minimal", "technical"]


DEFAULT_SECTION_TITLES: dict[str, str] = {
    "summary": "Professional Summary",
    "experience": "Professional Experience",
    "education": "Education & Academic Background",
    "skills": "Technical & Core Skills",
    "projects": "Featured Projects",
    "certifications": "Certifications & Accreditations",
    "languages": "Languages",
    "custom_sections": "Additional Information",
}


def resolve_section_title(section_id: str, custom_title: str | None = None) -> str:
    """Resolve the display title for a resume section.

    If custom_title is non-empty and not whitespace-only, return it stripped.
    Otherwise, fall back to the default title for that section identifier.
    """
    if custom_title and isinstance(custom_title, str) and custom_title.strip():
        return custom_title.strip()
    return DEFAULT_SECTION_TITLES.get(section_id, section_id.replace("_", " ").title())


class ResumeSectionTitleItem(BaseModel):
    id: str
    default_title: str = ""
    custom_title: str = ""
    resolved_title: str = ""


class ResumeSettings(BaseModel):
    template: ResumeTemplateType = "modern"
    theme_color: str = "#2563eb"
    font_family: str = "Inter"
    font_size: str = "10.5"
    document_size: Literal["A4", "LETTER"] = "A4"
    section_order: list[str] = Field(
        default_factory=lambda: [
            "summary",
            "experience",
            "education",
            "skills",
            "projects",
            "certifications",
            "languages",
            "custom_sections",
        ]
    )
    section_visibility: dict[str, bool] = Field(
        default_factory=lambda: {
            "profile": True,
            "summary": True,
            "experience": True,
            "education": True,
            "skills": True,
            "projects": True,
            "certifications": True,
            "languages": True,
            "custom_sections": True,
        }
    )
    section_titles: dict[str, str] = Field(
        default_factory=dict,
        description="Map of internal section IDs to user-customized display titles",
    )



class StructuredResumeCreate(BaseModel):
    title: str = Field(default="My Resume", min_length=1, max_length=255)
    is_default: bool = False
    structured_data: StructuredResumeData | None = None
    settings: ResumeSettings | None = None
    target_job_id: int | None = None
    source_resume_id: int | None = None


class StructuredResumeUpdate(BaseModel):
    title: str | None = None
    is_default: bool | None = None
    structured_data: StructuredResumeData | None = None
    settings: ResumeSettings | None = None


class StructuredResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    is_active: bool
    is_default: bool
    target_job_id: int | None = None
    source_resume_id: int | None = None
    structured_data: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class StructuredResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    is_active: bool
    is_default: bool
    target_job_id: int | None = None
    source_resume_id: int | None = None
    created_at: datetime
    updated_at: datetime
    template: str = "modern"
    theme_color: str = "#2563eb"
    skills_count: int = 0
    experience_count: int = 0
    education_count: int = 0


class ResumeDuplicateRequest(BaseModel):
    new_title: str | None = None


class ResumeTailorSuggestionSummary(BaseModel):
    original: str = ""
    suggested: str = ""
    reason: str = ""


class ResumeTailorSuggestionExperience(BaseModel):
    item_id: str
    company: str
    title: str
    original_description: str
    suggested_highlights: list[str] = Field(default_factory=list)
    reason: str = ""


class ResumeTailorSuggestions(BaseModel):
    job_id: int
    job_title: str
    base_resume_id: int
    base_resume_title: str
    match_score: int
    summary: ResumeTailorSuggestionSummary
    skills_to_emphasize: list[str] = Field(default_factory=list)
    missing_job_skills: list[str] = Field(default_factory=list)
    experience_refinements: list[ResumeTailorSuggestionExperience] = Field(default_factory=list)
    key_advice: list[str] = Field(default_factory=list)


class ResumeSaveTailoredCopyRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    apply_suggested_summary: bool = True
    apply_emphasized_skills: bool = True
    accepted_experience_refinements: list[str] = Field(default_factory=list)
