"""Pure provider-mode validation with typed, fail-closed errors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

Environment = Literal["local", "ci", "public"]


class EmbeddingMode(StrEnum):
    """Embedding uses either an explicit fixture or the pinned local reference."""

    FIXTURE = "fixture"
    REFERENCE = "reference"


class GenerationMode(StrEnum):
    """Generation may be explicitly disabled without selecting a provider."""

    DISABLED = "disabled"
    FIXTURE = "fixture"
    LIVE = "live"


class LiveProvider(StrEnum):
    """Governed live provider selected by an explicit story approval."""

    OPENROUTER = "openrouter"


class ProviderConfigurationErrorCode(StrEnum):
    """Stable reasons that provider configuration is rejected."""

    PUBLIC_FIXTURE_FORBIDDEN = "provider.public_fixture_forbidden"
    REFERENCE_SNAPSHOT_REQUIRED = "provider.reference_snapshot_required"
    LIVE_PROVIDER_NOT_CONFIGURED = "provider.live_not_configured"
    LIVE_PROVIDER_UNSUPPORTED = "provider.live_unsupported"
    LIVE_PROVIDER_SECRET_REQUIRED = "provider.live_secret_required"
    LIVE_BUDGET_INVALID = "provider.live_budget_invalid"


class ProviderConfigurationError(RuntimeError):
    """A typed configuration failure that never triggers a fallback."""

    def __init__(self, code: ProviderConfigurationErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ProviderConfiguration:
    """Validated provider modes consumed by later application composition."""

    environment: Environment
    embedding_mode: EmbeddingMode
    generation_mode: GenerationMode
    reference_snapshot_path: str | None
    live_provider: LiveProvider | None = None
    live_model: str | None = None
    live_budget_usd: float | None = None
    live_stop_usd: float | None = None


def validate_provider_configuration(
    *,
    environment: Environment,
    embedding_mode: EmbeddingMode,
    generation_mode: GenerationMode,
    reference_snapshot_path: str | None,
    live_provider: LiveProvider | None,
    live_model: str | None,
    live_api_key_configured: bool,
    live_budget_usd: float,
    live_stop_usd: float,
) -> ProviderConfiguration:
    """Validate explicit modes without constructing or substituting an adapter."""

    if environment == "public" and (
        embedding_mode is EmbeddingMode.FIXTURE or generation_mode is GenerationMode.FIXTURE
    ):
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.PUBLIC_FIXTURE_FORBIDDEN,
            "fixture providers are not valid in public mode",
        )

    normalized_snapshot_path = (
        reference_snapshot_path.strip() if reference_snapshot_path is not None else None
    )
    if embedding_mode is EmbeddingMode.REFERENCE and not normalized_snapshot_path:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.REFERENCE_SNAPSHOT_REQUIRED,
            "reference embedding mode requires a pre-provisioned snapshot path",
        )

    normalized_live_model = live_model.strip() if live_model is not None else None
    if generation_mode is GenerationMode.LIVE:
        if live_provider is None:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.LIVE_PROVIDER_NOT_CONFIGURED,
                "live generation requires an explicitly approved provider",
            )
        if live_provider is not LiveProvider.OPENROUTER:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.LIVE_PROVIDER_UNSUPPORTED,
                "live generation provider is not approved",
            )
        if not normalized_live_model:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.LIVE_PROVIDER_NOT_CONFIGURED,
                "live generation requires an explicitly approved model",
            )
        if not live_api_key_configured:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.LIVE_PROVIDER_SECRET_REQUIRED,
                "live generation requires a server-side provider secret",
            )
        if live_budget_usd <= 0 or live_stop_usd <= 0 or live_stop_usd > live_budget_usd:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.LIVE_BUDGET_INVALID,
                "live generation budget and stop limit are invalid",
            )
    return ProviderConfiguration(
        environment=environment,
        embedding_mode=embedding_mode,
        generation_mode=generation_mode,
        reference_snapshot_path=normalized_snapshot_path,
        live_provider=live_provider if generation_mode is GenerationMode.LIVE else None,
        live_model=normalized_live_model if generation_mode is GenerationMode.LIVE else None,
        live_budget_usd=live_budget_usd if generation_mode is GenerationMode.LIVE else None,
        live_stop_usd=live_stop_usd if generation_mode is GenerationMode.LIVE else None,
    )
