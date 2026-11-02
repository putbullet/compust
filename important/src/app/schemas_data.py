"""
Pydantic schemas for Compust Data Management, Guided Import, Database Settings & Doctor.
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
    type: str  # "mysql" | "sqlite" | "sql_dump"
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
    dry_run: bool = False


class ImportExecuteResponse(BaseModel):
    success: bool
    message: str
    batch_id: str | None = None
    is_dry_run: bool = False
    backup_file: str | None = None
    users_imported: int = 0
    companies_imported: int = 0
    jobs_imported: int = 0
    applications_imported: int = 0
    contacts_imported: int = 0
    resumes_imported: int = 0
    files_copied: int = 0
    skipped_counts: dict[str, int] = Field(default_factory=dict)
    merged_counts: dict[str, int] = Field(default_factory=dict)


class ImportHistoryItem(BaseModel):
    batch_id: str
    source_type: str
    source_location: str
    strategy: str
    imported_at: str
    counts: dict[str, int] = Field(default_factory=dict)
    status: str
    undone_at: str | None = None


class UndoImportResponse(BaseModel):
    success: bool
    batch_id: str
    message: str
    removed_counts: dict[str, int] = Field(default_factory=dict)
    backup_file: str | None = None


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


# --- Database Linking & Doctor Schemas ---

class DetectedServerInfo(BaseModel):
    host: str
    port: int
    reachable: bool
    is_mysql: bool
    server_version: str


class DatabaseDetectResponse(BaseModel):
    detected_servers: list[DetectedServerInfo] = Field(default_factory=list)


class DatabaseTestRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "compust"


class DatabaseTestResponse(BaseModel):
    success: bool
    error_code: str | None = None
    message: str
    server_version: str | None = None
    database_exists: bool = False
    schema_state: str  # "empty" | "compatible" | "outdated" | "foreign" | "unreachable" | "auth_failed"
    table_counts: dict[str, int] = Field(default_factory=dict)


class DatabaseCreateRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "compust"


class DatabaseSwitchRequest(BaseModel):
    target_engine: str  # "mysql" | "sqlite"
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "compust"
    run_migrations: bool = True


class DatabaseActiveInfoResponse(BaseModel):
    engine: str
    location: str
    is_sqlite: bool
    size_mb: float | None = None
    table_counts: dict[str, int] = Field(default_factory=dict)
    schema_synced: bool
    missing_tables: list[str] = Field(default_factory=list)
    missing_columns: dict[str, list[str]] = Field(default_factory=dict)
    is_fallback_active: bool = False
    configured: bool = False


class DoctorStatusResponse(BaseModel):
    is_healthy: bool
    active_engine: str
    active_location: str
    is_sqlite: bool
    size_mb: float | None = None
    schema_synced: bool
    missing_tables: list[str] = Field(default_factory=list)
    missing_columns: dict[str, list[str]] = Field(default_factory=dict)
    table_counts: dict[str, int] = Field(default_factory=dict)
    is_fallback_active: bool = False
    available_backups: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None


class DoctorRepairResponse(BaseModel):
    success: bool
    message: str
    is_synced: bool
    created_tables: list[str] = Field(default_factory=list)
    added_columns: dict[str, list[str]] = Field(default_factory=dict)
    applied_migrations: list[str] = Field(default_factory=list)
    backup_file: str | None = None
