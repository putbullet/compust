from pydantic import BaseModel, Field


class ResumePromptResponse(BaseModel):
    """Schema for tailored resume prompt generation endpoint."""

    success: bool = Field(True, description="Whether prompt generation succeeded")
    has_profile: bool = Field(True, description="Whether candidate has profile data (false if empty)")
    char_count: int = Field(0, description="Total characters in generated prompt")
    prompt: str = Field("", description="Full ready-to-paste markdown prompt")
    job_id: str = Field("", description="Job identifier")
    job_title: str = Field("", description="Target job title")
    company_name: str = Field("", description="Target employer name")
    include_contact: bool = Field(True, description="Whether contact details were included")
    source_resume_title: str | None = Field(None, description="Active resume name")
    source_resume_id: int | None = Field(None, description="Active resume ID")
    profile_version: str = Field("", description="Version hash of the candidate profile")
    has_experience: bool = Field(True, description="Whether the profile contains work experience")
    counts: dict[str, int] = Field(default_factory=dict, description="Counts of items included in profile")
    error: str | None = Field(None, description="Diagnostic error or guidance message")
