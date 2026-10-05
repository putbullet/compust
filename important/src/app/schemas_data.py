"""
Pydantic schemas for Compust Data Management, Guided Import, and Backup/Restore.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class UserDataSummary(BaseModel):
    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    applications_count: int = 0
    contacts_count: int = 0
    resumes_count: int = 0


class ImportSourceInfo(BaseModel):
    id: str
    name: str
    type: str  # "mysql" | "sqlite"
    location: str
    reachable: bool
    status_message: str
    total_jobs: int = 0
    total_companies: int = 0
    users: list[UserDataSummary] = Field(default_factory=list)


class ImportSourcesResponse(BaseModel):
    sources: list[ImportSourceInfo]
    target_database_path: str
    target_database_type: str
    target_has_data: bool
    target_stats: dict[str, int] = Field(default_factory=dict)


class ImportPreviewRequest(BaseModel):
    source_id: str
    user_id: int | None = None
    email: str | None = None


class ImportPreviewResponse(BaseModel):
    source_id: str
    selected_user: UserDataSummary | None = None
    jobs_count: int = 0
    companies_count: int = 0
    applications_count: int = 0
    contacts_count: int = 0
    resumes_count: int = 0
    target_existing_jobs: int = 0
    target_existing_applications: int = 0
    warning: str | None = None


class ImportExecuteRequest(BaseModel):
    source_id: str
    user_id: int | None = None
    email: str | None = None
    conflict_strategy: str = "merge"  # "merge" | "skip" | "overwrite"


class ImportExecuteResponse(BaseModel):
    success: bool
    message: str
    backup_file: str | None = None
    users_imported: int = 0
    companies_imported: int = 0
    jobs_imported: int = 0
    applications_imported: int = 0
    contacts_imported: int = 0
    resumes_imported: int = 0
    files_copied: int = 0


class BackupExportResponse(BaseModel):
    success: bool
    filename: str
    size_bytes: int
    download_url: str
    created_at: str
    stats: dict[str, int] = Field(default_factory=dict)


class BackupRestoreResponse(BaseModel):
    success: bool
    message: str
    safety_backup: str | None = None
    restored_stats: dict[str, int] = Field(default_factory=dict)
