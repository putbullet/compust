from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Compust API", validation_alias="COMPUST_APP_NAME")
    debug: bool = Field(default=False, validation_alias="COMPUST_DEBUG")
    database_url: str = Field(
        default="mysql+pymysql://root:@127.0.0.1:3306/compust",
        validation_alias="COMPUST_DATABASE_URL",
    )
    db_pool_pre_ping: bool = Field(
        default=True,
        validation_alias="COMPUST_DB_POOL_PRE_PING",
    )
    jwt_secret_key: str = Field(
        default="compust-secret-key-for-development-change-in-production-12345",
        validation_alias="COMPUST_JWT_SECRET",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 1 day
    cors_allowed_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        validation_alias="COMPUST_CORS_ALLOWED_ORIGINS",
    )
    scraper_request_timeout: float = Field(
        default=20.0,
        validation_alias="COMPUST_SCRAPER_TIMEOUT",
    )
    scraper_user_agent: str = Field(
        default="Compust/0.1 (+local career research; https://compust.ma)",
        validation_alias="COMPUST_SCRAPER_USER_AGENT",
    )
    scraper_request_delay_seconds: float = Field(
        default=1.0,
        validation_alias="COMPUST_SCRAPER_DELAY",
    )
    scraper_max_pages_limit: int = Field(
        default=20,
        validation_alias="COMPUST_SCRAPER_PAGE_LIMIT",
    )
    ollama_url: str = Field(
        default="http://127.0.0.1:11434",
        validation_alias="COMPUST_OLLAMA_URL",
    )
    default_ai_model: str | None = Field(
        default=None,
        validation_alias="COMPUST_DEFAULT_AI_MODEL",
    )
    stale_job_missed_runs_threshold: int = Field(
        default=3,
        validation_alias="COMPUST_STALE_JOB_MISSED_RUNS",
    )
    job_titles_path: str | None = Field(
        default=None,
        validation_alias="COMPUST_JOB_TITLES_PATH",
    )
    scraper_enable_browser_fallback: bool = Field(
        default=True,
        validation_alias="COMPUST_SCRAPER_ENABLE_BROWSER_FALLBACK",
    )
    scraper_browser_timeout_seconds: float = Field(
        default=15.0,
        validation_alias="COMPUST_SCRAPER_BROWSER_TIMEOUT",
    )
    scraper_browser_headless: bool = Field(
        default=True,
        validation_alias="COMPUST_SCRAPER_BROWSER_HEADLESS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
