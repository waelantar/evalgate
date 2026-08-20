"""Framework-free outbound ports owned by the application layer."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingVector,
    GenerationInput,
    GenerationOutput,
    ProviderIdentity,
)


@runtime_checkable
class EmbeddingPort(Protocol):
    """Embed text through an explicitly identified implementation."""

    @property
    def identity(self) -> ProviderIdentity: ...

    @property
    def dimension(self) -> int: ...

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]: ...


@runtime_checkable
class GenerationPort(Protocol):
    """Generate text through an explicitly identified implementation."""

    @property
    def identity(self) -> ProviderIdentity: ...

    async def generate(self, request: GenerationInput) -> GenerationOutput: ...


@runtime_checkable
class ClockPort(Protocol):
    """Supply an aware application timestamp."""

    def now(self) -> datetime: ...


@runtime_checkable
class IdentityPort(Protocol):
    """Supply a new opaque application identifier."""

    def new_id(self) -> UUID: ...
