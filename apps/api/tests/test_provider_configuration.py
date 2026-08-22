"""Fail-closed provider configuration tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evalgate.application.provider_configuration import (
    EmbeddingMode,
    GenerationMode,
    ProviderConfigurationError,
    ProviderConfigurationErrorCode,
)
from evalgate.config import Settings, get_settings


def test_local_fixture_modes_are_explicit() -> None:
    configuration = Settings().provider_configuration()

    assert configuration.embedding_mode is EmbeddingMode.FIXTURE
    assert configuration.generation_mode is GenerationMode.FIXTURE


def test_public_mode_rejects_fixture_providers() -> None:
    settings = Settings(
        environment="public",
        embedding_mode=EmbeddingMode.FIXTURE,
        generation_mode=GenerationMode.DISABLED,
    )

    with pytest.raises(ProviderConfigurationError) as captured:
        settings.provider_configuration()

    assert captured.value.code is ProviderConfigurationErrorCode.PUBLIC_FIXTURE_FORBIDDEN


def test_reference_mode_requires_preprovisioned_snapshot() -> None:
    settings = Settings(
        embedding_mode=EmbeddingMode.REFERENCE,
        generation_mode=GenerationMode.DISABLED,
    )

    with pytest.raises(ProviderConfigurationError) as captured:
        settings.provider_configuration()

    assert captured.value.code is ProviderConfigurationErrorCode.REFERENCE_SNAPSHOT_REQUIRED


def test_live_mode_returns_typed_error_without_fixture_fallback() -> None:
    settings = Settings(generation_mode=GenerationMode.LIVE)

    with pytest.raises(ProviderConfigurationError) as captured:
        settings.provider_configuration()

    assert captured.value.code is ProviderConfigurationErrorCode.LIVE_PROVIDER_NOT_CONFIGURED


def test_public_reference_mode_accepts_only_an_explicit_snapshot() -> None:
    configuration = Settings(
        environment="public",
        embedding_mode=EmbeddingMode.REFERENCE,
        generation_mode=GenerationMode.DISABLED,
        reference_embedding_snapshot=" verified-snapshot ",
    ).provider_configuration()

    assert configuration.embedding_mode is EmbeddingMode.REFERENCE
    assert configuration.generation_mode is GenerationMode.DISABLED
    assert configuration.reference_snapshot_path == "verified-snapshot"


def test_unknown_mode_is_rejected_by_typed_settings() -> None:
    with pytest.raises(ValidationError):
        Settings(embedding_mode="live")  # type: ignore[arg-type]


def test_process_settings_fail_closed_before_runtime_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("EVALGATE_GENERATION_MODE", "live")
    try:
        with pytest.raises(ProviderConfigurationError) as captured:
            get_settings()
    finally:
        get_settings.cache_clear()

    assert captured.value.code is ProviderConfigurationErrorCode.LIVE_PROVIDER_NOT_CONFIGURED
