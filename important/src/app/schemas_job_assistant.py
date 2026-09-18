"""
schemas_job_assistant.py
========================
Pydantic schemas for the Job-Specific Resume & Career Assistant feature.
Separate from schemas_resume.py to keep concerns organized.
Used exclusively by the /resumes/{id}/job-target/* endpoints.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class SupportedLanguage(str, Enum):
    EN = "en"
    FR = "fr"
    DE = "de"
    ES = "es"


class ExternalJobInput(BaseModel):
    """Job supplied by the user - may have been found anywhere."""

    model_config = ConfigDict(extra="ignore")

    target_role: str = Field(..., min_length=2, max_length=300)
    job_description: str = Field(..., min_length=50, max_length=12000)
    additional_information: str = Field(default="", max_length=2000)
    language: SupportedLanguage = Field(default=SupportedLanguage.EN)

    @field_validator("target_role", "job_description", mode="before")
    @classmethod
    def _strip(cls, v: Any) -> str:
        return str(v).strip() if v is not None else ""


# ---------------------------------------------------------------------------
# Job analysis output - requirements
# ---------------------------------------------------------------------------

class RequirementCategory(str, Enum):
    TECHNICAL_SKILL = "technical_skill"
    TOOL = "tool"
    METHODOLOGY = "methodology"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    LANGUAGE = "language"
    CERTIFICATION = "certification"
    DOMAIN = "domain"
    SOFT_SKILL = "soft_skill"
    ATS_KEYWORD = "ats_keyword"
    OTHER = "other"


class RequirementImportance(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice_to_have"


class JobRequirement(BaseModel):
    text: str
    category: RequirementCategory = RequirementCategory.OTHER
    importance: RequirementImportance = RequirementImportance.REQUIRED
    raw_keyword: str = ""


# ---------------------------------------------------------------------------
# Match analysis
# ---------------------------------------------------------------------------

class MatchStatus(str, Enum):
    STRONG = "strong"
    PARTIAL = "partial"
    MISSING = "missing"
    VERIFY = "verify"
    UNKNOWN = "unknown"


class CandidateEvidenceMatch(BaseModel):
    requirement: str
    requirement_category: RequirementCategory = RequirementCategory.OTHER
    match_status: MatchStatus = MatchStatus.UNKNOWN
    evidence_sources: list[str] = Field(default_factory=list)
    note: str = ""


class MatchAnalysis(BaseModel):
    strong_matches: list[CandidateEvidenceMatch] = Field(default_factory=list)
    partial_matches: list[CandidateEvidenceMatch] = Field(default_factory=list)
    missing_or_unconfirmed: list[CandidateEvidenceMatch] = Field(default_factory=list)
    verify_items: list[CandidateEvidenceMatch] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Deterministic scoring - reproducible, NOT from LLM
# ---------------------------------------------------------------------------

class DeterministicScore(BaseModel):
    """Scores computed deterministically. LLM does NOT produce these values."""
    technical_skills: float = Field(default=0.0, ge=0, le=10)
    experience_alignment: float = Field(default=0.0, ge=0, le=10)
    education: float = Field(default=0.0, ge=0, le=10)
    languages: float = Field(default=0.0, ge=0, le=10)
    ats_keywords: float = Field(default=0.0, ge=0, le=10)
    overall: float = Field(default=0.0, ge=0, le=10)
    methodology: str = (
        "Deterministic: skill overlap / job requirements (technical), "
        "experience titles / description keywords (experience), "
        "education field match (education), language match (languages), "
        "ATS keyword density (ats_keywords). Overall = weighted mean."
    )


# ---------------------------------------------------------------------------
# Resume recommendations
# ---------------------------------------------------------------------------

class RecommendationType(str, Enum):
    KEEP = "keep"
    EMPHASIZE = "emphasize"
    REWRITE = "rewrite"
    MOVE = "move"
    ADD = "add"
    MISSING = "missing"
    VERIFY = "verify"
    REDUCE = "reduce"
    REMOVE = "remove"


class ResumeRecommendation(BaseModel):
    id: str = ""
    rec_type: RecommendationType
    section: str
    item_id: str = ""
    item_label: str = ""
    current_text: str = ""
    suggested_text: str = ""
    reason: str = ""
    evidence_sources: list[str] = Field(default_factory=list)
    grounded: bool = True  # Anti-hallucination flag


# ---------------------------------------------------------------------------
# Application materials
# ---------------------------------------------------------------------------

class MaterialType(str, Enum):
    COLD_EMAIL = "cold_email"
    SHORT_MESSAGE = "short_message"
    MOTIVATION_LETTER = "motivation_letter"


class ApplicationMaterial(BaseModel):
    material_type: MaterialType
    subject: str = ""
    body: str = ""
    placeholders: list[str] = Field(default_factory=list)
    language: str = "en"
    generated: bool = False
    error: str = ""


# ---------------------------------------------------------------------------
# Stage 5 - Interview & STAR Prep
# ---------------------------------------------------------------------------

class STARResponse(BaseModel):
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""


class InterviewQuestionType(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    DOMAIN = "domain"
    QUALIFICATION_GAP = "qualification_gap"


class InterviewQuestion(BaseModel):
    id: str = ""
    question: str
    question_type: InterviewQuestionType = InterviewQuestionType.BEHAVIORAL
    category: str = ""
    context_reason: str = ""
    suggested_star: STARResponse = Field(default_factory=STARResponse)
    handling_missing_skill: str = ""


class InterviewPrep(BaseModel):
    questions: list[InterviewQuestion] = Field(default_factory=list)
    key_focus_areas: list[str] = Field(default_factory=list)
    confidence_tip: str = ""


# ---------------------------------------------------------------------------
# Full analysis result
# ---------------------------------------------------------------------------

class JobTargetAnalysisResult(BaseModel):
    resume_id: int
    target_role: str
    language: str
    job_requirements: list[JobRequirement] = Field(default_factory=list)
    match_analysis: MatchAnalysis = Field(default_factory=MatchAnalysis)
    deterministic_score: DeterministicScore = Field(default_factory=DeterministicScore)
    resume_recommendations: list[ResumeRecommendation] = Field(default_factory=list)
    cold_email: ApplicationMaterial = Field(
        default_factory=lambda: ApplicationMaterial(material_type=MaterialType.COLD_EMAIL)
    )
    short_message: ApplicationMaterial = Field(
        default_factory=lambda: ApplicationMaterial(material_type=MaterialType.SHORT_MESSAGE)
    )
    motivation_letter: ApplicationMaterial = Field(
        default_factory=lambda: ApplicationMaterial(material_type=MaterialType.MOTIVATION_LETTER)
    )
    interview_prep: InterviewPrep = Field(default_factory=InterviewPrep)
    ollama_used: bool = False
    ollama_model: str | None = None
    partial_failure: bool = False
    partial_failure_detail: str = ""
    data_conflicts: list[str] = Field(default_factory=list)



# ---------------------------------------------------------------------------
# Save tailored copy request
# ---------------------------------------------------------------------------

class SaveTailoredFromJobTargetRequest(BaseModel):
    new_title: str = Field(..., min_length=1, max_length=255)
    accepted_recommendation_ids: list[str] = Field(default_factory=list)
    accepted_recommendations: list[ResumeRecommendation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Export request
# ---------------------------------------------------------------------------

class ExportDocumentRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=20000)
    file_format: str = Field(default="pdf", pattern="^(pdf|docx)$")
    suggested_filename: str = Field(default="document", max_length=200)

    @field_validator("suggested_filename", mode="before")
    @classmethod
    def _sanitize_filename(cls, v: Any) -> str:
        if not v:
            return "document"
        safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(v))
        return safe.strip("_")[:200] or "document"


# ---------------------------------------------------------------------------
# Single material regeneration request
# ---------------------------------------------------------------------------

class RegenerateMaterialRequest(BaseModel):
    material_type: MaterialType
    target_role: str = Field(..., min_length=2, max_length=300)
    job_description: str = Field(..., min_length=50, max_length=12000)
    additional_information: str = Field(default="", max_length=2000)
    language: SupportedLanguage = Field(default=SupportedLanguage.EN)

    @field_validator("target_role", "job_description", mode="before")
    @classmethod
    def _strip(cls, v: Any) -> str:
        return str(v).strip() if v is not None else ""



# ---------------------------------------------------------------------------
# Candidate context (internal)
# ---------------------------------------------------------------------------

class CandidateContextProfile(BaseModel):
    full_name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""


class CandidateContextSkill(BaseModel):
    name: str
    category: str = ""
    proficiency: str = ""
    source: str = ""  # "resume" | "profile" | "both"


class CandidateContextExperience(BaseModel):
    id: str = ""
    title: str = ""
    company: str = ""
    description: str = ""
    highlights: list[str] = Field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    source: str = "resume"


class CandidateContextEducation(BaseModel):
    id: str = ""
    institution: str = ""
    degree: str = ""
    field: str = ""
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    source: str = "resume"


class CandidateContextProject(BaseModel):
    id: str = ""
    name: str = ""
    description: str = ""
    technologies: str = ""
    source: str = "resume"


class CandidateContextLanguage(BaseModel):
    language: str = ""
    proficiency: str = ""
    source: str = "resume"


class CandidateContextCertification(BaseModel):
    id: str = ""
    name: str = ""
    issuer: str = ""
    source: str = "resume"


class CandidateContext(BaseModel):
    """
    Merged, conflict-checked representation of the candidate.
    Primary source: selected resume. Secondary: profile (fills gaps only).
    Conflicts are flagged, not silently resolved.
    """
    profile: CandidateContextProfile = Field(default_factory=CandidateContextProfile)
    skills: list[CandidateContextSkill] = Field(default_factory=list)
    experience: list[CandidateContextExperience] = Field(default_factory=list)
    education: list[CandidateContextEducation] = Field(default_factory=list)
    projects: list[CandidateContextProject] = Field(default_factory=list)
    languages: list[CandidateContextLanguage] = Field(default_factory=list)
    certifications: list[CandidateContextCertification] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
