"""Provider-neutral values shared by the application ports."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class ProviderMode(StrEnum):
    """A provider execution class that must remain visible to callers."""

    FIXTURE = "fixture"
    REFERENCE = "reference"
    LIVE = "live"


class EmbeddingRole(StrEnum):
    """The semantic role of text sent to an embedding port."""

    QUERY = "query"
    DOCUMENT = "document"


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    """The explicit identity attached to provider output."""

    mode: ProviderMode
    name: str
    revision: str


@dataclass(frozen=True, slots=True)
class EmbeddingInput:
    """One text value and its embedding role."""

    text: str
    role: EmbeddingRole

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("embedding text must not be empty")


@dataclass(frozen=True, slots=True)
class EmbeddingVector:
    """One finite vector whose provider identity cannot be omitted."""

    values: tuple[float, ...]
    identity: ProviderIdentity

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("embedding vector must not be empty")
        if not all(isfinite(value) for value in self.values):
            raise ValueError("embedding vector values must be finite")


@dataclass(frozen=True, slots=True)
class GenerationInput:
    """Provider-neutral text submitted to a generation port."""

    text: str

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("generation input must not be empty")


@dataclass(frozen=True, slots=True)
class GenerationUsage:
    """Bounded usage and cost evidence returned by a live generation provider."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0 or self.total_tokens < 0:
            raise ValueError("generation token usage must be non-negative")
        if self.total_tokens < self.input_tokens + self.output_tokens:
            raise ValueError("generation total tokens must cover input and output tokens")
        if not isfinite(self.cost_usd) or self.cost_usd < 0:
            raise ValueError("generation cost must be a finite non-negative value")


@dataclass(frozen=True, slots=True)
class GenerationOutput:
    """Generated text with an explicit provider identity."""

    text: str
    identity: ProviderIdentity
    usage: GenerationUsage | None = None
