"""Typed runtime configuration with safe local defaults."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from evalgate.application.operations import GenerationLimits, build_generation_limits
from evalgate.application.provider_configuration import (
    EmbeddingMode,
    GenerationMode,
    LiveProvider,
    ProviderConfiguration,
    validate_provider_configuration,
)
from evalgate.application.runtime_security import (
    Environment,
    RuntimeSecurityConfiguration,
    build_runtime_security_configuration,
    validate_provider_base_url,
)


class Settings(BaseSettings):
    """EvalGate settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_prefix="EVALGATE_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Environment = "local"
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://evalgate:evalgate_local_only@127.0.0.1:5432/evalgate"
    )
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    embedding_mode: EmbeddingMode = EmbeddingMode.FIXTURE
    generation_mode: GenerationMode = GenerationMode.FIXTURE
    reference_embedding_snapshot: str | None = None
    live_provider: LiveProvider | None = None
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "deepseek/deepseek-v4-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    live_eval_budget_usd: float = Field(default=4.60, gt=0)
    live_eval_stop_usd: float = Field(default=4.14, gt=0)
    allowed_origins: str = "http://localhost:5173"
    trusted_proxy_addresses: str = ""
    request_body_limit_bytes: int = Field(default=16_384, ge=1024, le=65_536)
    request_timeout_seconds: float = Field(default=30.0, gt=0, le=60)
    rate_identity_ttl_seconds: int = Field(default=300, ge=60, le=3600)
    rate_identity_secret: SecretStr | None = None
    generation_maximum_input_tokens: int | None = Field(default=None, ge=1)
    generation_maximum_output_tokens: int | None = Field(default=None, ge=1)
    generation_per_client_concurrency: int | None = Field(default=None, ge=1)
    generation_global_concurrency: int | None = Field(default=None, ge=1)
    generation_daily_request_allowance: int | None = Field(default=None, ge=1)
    generation_provider_account_cap_usd: float | None = Field(default=None, gt=0)
    generation_cooldown_seconds: float = Field(default=0, ge=0, le=3600)
    generation_kill_switch_enabled: bool = False

    def provider_configuration(self) -> ProviderConfiguration:
        """Resolve explicit provider modes or raise a typed, fail-closed error."""

        return validate_provider_configuration(
            environment=self.environment,
            embedding_mode=self.embedding_mode,
            generation_mode=self.generation_mode,
            reference_snapshot_path=self.reference_embedding_snapshot,
            live_provider=self.live_provider,
            live_model=self.openrouter_model,
            live_api_key_configured=self.openrouter_api_key is not None
            and bool(self.openrouter_api_key.get_secret_value().strip()),
            live_budget_usd=self.live_eval_budget_usd,
            live_stop_usd=self.live_eval_stop_usd,
        )

    def runtime_security_configuration(self) -> RuntimeSecurityConfiguration:
        """Resolve the environment and HTTP security policy fail-closed."""

        validate_provider_base_url(self.openrouter_base_url)
        return build_runtime_security_configuration(
            environment=self.environment,
            allowed_origins=self.allowed_origins,
            trusted_proxy_addresses=self.trusted_proxy_addresses,
            request_body_limit_bytes=self.request_body_limit_bytes,
            request_timeout_seconds=self.request_timeout_seconds,
            rate_identity_ttl_seconds=self.rate_identity_ttl_seconds,
            rate_identity_secret=(
                self.rate_identity_secret.get_secret_value()
                if self.rate_identity_secret is not None
                else None
            ),
        )

    def generation_limits(self) -> GenerationLimits | None:
        """Resolve a complete public generation-control configuration or fail closed."""

        return build_generation_limits(
            public_http=self.environment == "public",
            maximum_input_tokens=self.generation_maximum_input_tokens,
            maximum_output_tokens=self.generation_maximum_output_tokens,
            per_client_concurrency=self.generation_per_client_concurrency,
            global_concurrency=self.generation_global_concurrency,
            daily_request_allowance=self.generation_daily_request_allowance,
            provider_account_cap_usd=self.generation_provider_account_cap_usd,
            cooldown_seconds=self.generation_cooldown_seconds,
        )


@lru_cache
def get_settings() -> Settings:
    """Return one validated, immutable-by-convention settings instance per process."""

    settings = Settings()
    settings.provider_configuration()
    settings.runtime_security_configuration()
    settings.generation_limits()
    return settings
