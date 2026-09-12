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
