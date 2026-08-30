"""Framework-free grounded-answer values and citation invariants."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from evalgate.domain.providers import ProviderIdentity
from evalgate.domain.search import IndexIdentity, SearchEvidence

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class AnswerMode(StrEnum):
    """Explicitly selected answer execution behavior."""

    RETRIEVAL_ONLY = "retrieval_only"
    FIXTURE = "fixture"


class AnswerStatus(StrEnum):
    """Stable grounded-answer result states."""

    RETRIEVAL_ONLY = "retrieval_only"
    ANSWERED = "answered"
    INSUFFICIENT_SUPPORT = "insufficient_support"


@dataclass(frozen=True, slots=True)
class Citation:
    """Server-derived citation metadata for one answer span and evidence item."""

    answer_start: int
    answer_end: int
    claim: str
    evidence_id: UUID
    document_id: UUID
    source_key: str
    title: str
    license_id: str
    provenance: str
    section_key: str
    source_start: int
    source_end: int
    span_sha256: str
    quote: str

    def __post_init__(self) -> None:
        if self.answer_start < 0 or self.answer_end <= self.answer_start:
            raise ValueError("citation answer offsets must form a non-empty span")
        for value, label in (
            (self.claim, "citation claim"),
            (self.source_key, "citation source key"),
            (self.title, "citation source title"),
            (self.license_id, "citation license ID"),
            (self.provenance, "citation provenance"),
            (self.section_key, "citation section key"),
            (self.quote, "citation quote"),
        ):
            if not value.strip():
                raise ValueError(f"{label} must not be empty")
        if self.source_start < 0 or self.source_end <= self.source_start:
            raise ValueError("citation source offsets must form a non-empty span")
        if _SHA256_PATTERN.fullmatch(self.span_sha256) is None:
            raise ValueError("citation span identity must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class AnswerResult:
    """Transport-independent retrieval and grounded-answer result."""

    mode: AnswerMode
    status: AnswerStatus
    prompt_policy_id: str
    prompt_policy_version: str
    prompt_policy_sha256: str
    index: IndexIdentity
    evidence: tuple[SearchEvidence, ...]
    answer: str | None
    citations: tuple[Citation, ...]
    generation_identity: ProviderIdentity | None

    def __post_init__(self) -> None:
        if not self.prompt_policy_id or not self.prompt_policy_version:
            raise ValueError("answer prompt policy identity must not be empty")
        if _SHA256_PATTERN.fullmatch(self.prompt_policy_sha256) is None:
            raise ValueError("answer prompt policy hash must be a lowercase SHA-256 digest")
        if self.status is AnswerStatus.RETRIEVAL_ONLY:
            if self.mode is not AnswerMode.RETRIEVAL_ONLY:
                raise ValueError("retrieval-only status requires retrieval-only mode")
            if self.answer is not None or self.citations or self.generation_identity is not None:
                raise ValueError("retrieval-only result must not contain generation output")
            return
        if self.mode is not AnswerMode.FIXTURE or self.generation_identity is None:
            raise ValueError("generated answer requires an explicit generation identity")
        if self.answer is None or not self.answer.strip():
            raise ValueError("generated answer text must not be empty")
        if self.status is AnswerStatus.ANSWERED and not self.citations:
            raise ValueError("answered result must contain a validated citation")
        if self.status is AnswerStatus.INSUFFICIENT_SUPPORT and self.citations:
            raise ValueError("insufficient-support result must not contain citations")
