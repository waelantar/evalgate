"""Typed runtime configuration with safe local defaults."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """EvalGate settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_prefix="EVALGATE_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["local", "ci", "public"] = "local"
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://evalgate:evalgate_local_only@127.0.0.1:5432/evalgate"
    )
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""

    return Settings()
