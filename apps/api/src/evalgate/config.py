"""Typed runtime configuration with safe local defaults."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from evalgate.application.provider_configuration import (
    EmbeddingMode,
    GenerationMode,
    ProviderConfiguration,
    validate_provider_configuration,
)


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
    embedding_mode: EmbeddingMode = EmbeddingMode.FIXTURE
    generation_mode: GenerationMode = GenerationMode.FIXTURE
    reference_embedding_snapshot: str | None = None

    def provider_configuration(self) -> ProviderConfiguration:
        """Resolve explicit provider modes or raise a typed, fail-closed error."""

        return validate_provider_configuration(
            environment=self.environment,
            embedding_mode=self.embedding_mode,
            generation_mode=self.generation_mode,
            reference_snapshot_path=self.reference_embedding_snapshot,
        )


@lru_cache
def get_settings() -> Settings:
    """Return one validated, immutable-by-convention settings instance per process."""

    settings = Settings()
    settings.provider_configuration()
    return settings
