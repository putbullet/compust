from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from .schemas import JobRead

ApplicationStatus = Literal["saved", "applied", "interviewing", "offer", "rejected"]


class ApplicationCreate(BaseModel):
    status: ApplicationStatus = "saved"
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    applied_at: datetime | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_id: int
    status: str
    notes: str | None = None
    applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    job: JobRead | None = None
