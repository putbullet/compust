from pydantic import BaseModel


class ScraperTelemetryRead(BaseModel):
    total_runs: int
    runs_by_status: dict[str, int]
    success_rate_percent: float
    avg_duration_seconds: float
    total_jobs_found: int
    total_jobs_added: int
    total_jobs_updated: int
    duplicate_rate_percent: float
    total_targets: int
    active_targets: int
    cooldown_targets: int
    robots_blocked_targets: int
    recent_errors: list[dict[str, str]]
