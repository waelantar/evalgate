"""Contract tests for framework-free ports and explicit fixtures."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from evalgate.adapters.fixtures import (
    FIXTURE_EMBEDDING_DIMENSION,
    DeterministicEmbeddingFixture,
    DeterministicGenerationFixture,
)
from evalgate.application.ports import (
    ClockPort,
    EmbeddingPort,
    GenerationPort,
    IdentityPort,
)
from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingRole,
    GenerationInput,
    ProviderMode,
)


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 20, tzinfo=UTC)


class _FixedIdentity:
    def new_id(self) -> UUID:
        return UUID("00000000-0000-0000-0000-000000000002")


def test_clock_and_identity_ports_are_structural() -> None:
    assert isinstance(_FixedClock(), ClockPort)
    assert isinstance(_FixedIdentity(), IdentityPort)


def test_embedding_fixture_is_repeatable_and_explicitly_labeled() -> None:
    adapter = DeterministicEmbeddingFixture()
    inputs = (
        EmbeddingInput(text="stable query", role=EmbeddingRole.QUERY),
        EmbeddingInput(text="stable document", role=EmbeddingRole.DOCUMENT),
    )

    first = asyncio.run(adapter.embed(inputs))
    second = asyncio.run(adapter.embed(inputs))

    assert isinstance(adapter, EmbeddingPort)
    assert first == second
    assert len(first) == len(inputs)
    assert all(len(result.values) == FIXTURE_EMBEDDING_DIMENSION for result in first)
    assert all(result.identity.mode is ProviderMode.FIXTURE for result in first)
    assert all("fixture" in result.identity.name for result in first)


def test_generation_fixture_is_repeatable_and_explicitly_labeled() -> None:
    adapter = DeterministicGenerationFixture()
    request = GenerationInput(text="contract mechanics")

    first = asyncio.run(adapter.generate(request))
    second = asyncio.run(adapter.generate(request))

    assert isinstance(adapter, GenerationPort)
    assert first == second
    assert first.identity.mode is ProviderMode.FIXTURE
    assert first.text.startswith("[fixture:")
