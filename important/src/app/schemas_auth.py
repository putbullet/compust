from pydantic import BaseModel, ConfigDict, Field


class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    first_name: str | None = None
    last_name: str | None = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResetPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    new_password: str = Field(min_length=6, max_length=128)


class UserPreferencesUpdate(BaseModel):
    preferred_job_type: str | None = None
    preferred_work_mode: str | None = None
    preferred_location: str | None = None
    min_salary: float | None = None
    max_salary: float | None = None
    salary_currency: str | None = None


class UserSkillUpdate(BaseModel):
    skills: list[str]


class UserPreferenceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preferred_job_type: str | None = None
    preferred_work_mode: str | None = None
    preferred_location: str | None = None
    min_salary: float | None = None
    max_salary: float | None = None
    salary_currency: str | None = None


from .schemas import CountryRead
from .schemas_profile import (
    UserEducationRead,
    UserExperienceRead,
    UserLanguageRead,
)


class UserCountryUpdate(BaseModel):
    country_ids: list[int]


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email_verified: bool
    preferences: UserPreferenceSchema | None = None
    skills: list[str] = []
    experience: list[UserExperienceRead] = []
    education: list[UserEducationRead] = []
    languages: list[UserLanguageRead] = []
    country_preferences: list[CountryRead] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


class JobMatchExplanation(BaseModel):
    job_id: int
    score: int
    positive_factors: list[str]
    missing_factors: list[str]
    category_scores: dict[str, int] = {}
