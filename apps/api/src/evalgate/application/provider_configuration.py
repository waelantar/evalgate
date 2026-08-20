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


class ProviderConfigurationErrorCode(StrEnum):
    """Stable reasons that provider configuration is rejected."""

    PUBLIC_FIXTURE_FORBIDDEN = "provider.public_fixture_forbidden"
    REFERENCE_SNAPSHOT_REQUIRED = "provider.reference_snapshot_required"
    LIVE_PROVIDER_NOT_CONFIGURED = "provider.live_not_configured"


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


def validate_provider_configuration(
    *,
    environment: Environment,
    embedding_mode: EmbeddingMode,
    generation_mode: GenerationMode,
    reference_snapshot_path: str | None,
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

    if generation_mode is GenerationMode.LIVE:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.LIVE_PROVIDER_NOT_CONFIGURED,
            "live generation is deferred until its governed provider decision",
        )

    return ProviderConfiguration(
        environment=environment,
        embedding_mode=embedding_mode,
        generation_mode=generation_mode,
        reference_snapshot_path=normalized_snapshot_path,
    )
