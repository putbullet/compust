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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
