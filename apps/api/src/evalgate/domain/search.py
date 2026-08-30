"""Framework-free values and pure fusion policy for explainable retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from uuid import UUID

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_nonempty(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} must not be empty")


def _require_sha256(value: str, label: str) -> None:
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


class RetrievalMode(StrEnum):
    """Internal retrieval branches used by search and later ablations."""

    LEXICAL = "lexical"
    VECTOR = "vector"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class RetrievalPolicy:
    """One immutable, versioned rank-fusion configuration."""

    policy_id: str
    lexical_candidate_depth: int
    vector_candidate_depth: int
    rrf_constant: int
    lexical_config_sha256: str

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("retrieval policy ID must not be empty")
        if self.lexical_candidate_depth < 1 or self.vector_candidate_depth < 1:
            raise ValueError("retrieval candidate depths must be positive")
        if self.rrf_constant < 1:
            raise ValueError("RRF constant must be positive")
        _require_sha256(self.lexical_config_sha256, "lexical configuration identity")


HYBRID_RRF_V1 = RetrievalPolicy(
    policy_id="hybrid-rrf-v1",
    lexical_candidate_depth=50,
    vector_candidate_depth=50,
    rrf_constant=60,
    lexical_config_sha256="4434b9362573450f668ed0014f428e744d3a7cc30f4630ebafedb22708b7d786",
)


@dataclass(frozen=True, slots=True)
class IndexIdentity:
    """Stored index and source-corpus identity selected for retrieval."""

    index_version_id: UUID
    index_key: str
    chunking_version: str
    chunking_policy_sha256: str
    lexical_config_sha256: str
    embedding_model: str
    embedding_revision: str
    embedding_checksum: str
    embedding_dimension: int
    corpus_version_id: UUID
    corpus_key: str
    corpus_version: str
    corpus_manifest_sha256: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.index_key, "index key"),
            (self.chunking_version, "chunking version"),
            (self.embedding_model, "embedding model"),
            (self.embedding_revision, "embedding revision"),
            (self.corpus_key, "corpus key"),
            (self.corpus_version, "corpus version"),
        ):
            _require_nonempty(value, label)
        for value, label in (
            (self.chunking_policy_sha256, "chunking policy identity"),
            (self.lexical_config_sha256, "lexical configuration identity"),
            (self.embedding_checksum, "embedding checksum"),
            (self.corpus_manifest_sha256, "corpus manifest identity"),
        ):
            _require_sha256(value, label)
        if self.embedding_dimension != 384:
            raise ValueError("index embedding dimension must be 384")


@dataclass(frozen=True, slots=True)
class EvidenceChunk:
    """One stable stored chunk with the provenance needed for inspection."""

    evidence_id: UUID
    document_id: UUID
    source_key: str
    title: str
    license_id: str
    provenance: str
    section_key: str
    source_start: int
    source_end: int
    content: str
    content_sha256: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_key, "source key"),
            (self.title, "source title"),
            (self.license_id, "license ID"),
            (self.provenance, "provenance"),
            (self.section_key, "section key"),
            (self.content, "evidence content"),
        ):
            _require_nonempty(value, label)
        _require_sha256(self.content_sha256, "evidence content identity")
        if self.source_start < 0 or self.source_end <= self.source_start:
            raise ValueError("evidence source offsets must form a non-empty span")


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """A component candidate with a one-based deterministic rank."""

    evidence: EvidenceChunk
    rank: int

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("component rank must be one-based")


@dataclass(frozen=True, slots=True)
class SearchEvidence:
    """Fused evidence with explainable component ranks."""

    rank: int
    evidence: EvidenceChunk
    lexical_rank: int | None
    vector_rank: int | None
    rrf_score: float

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("result rank must be one-based")
        if self.lexical_rank is None and self.vector_rank is None:
            raise ValueError("result must have at least one component rank")
        if self.lexical_rank is not None and self.lexical_rank < 1:
            raise ValueError("lexical rank must be one-based")
        if self.vector_rank is not None and self.vector_rank < 1:
            raise ValueError("vector rank must be one-based")
        if not isfinite(self.rrf_score) or self.rrf_score <= 0:
            raise ValueError("RRF score must be finite and positive")


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Application result independent of any inbound protocol."""

    policy_id: str
    index: IndexIdentity
    evidence: tuple[SearchEvidence, ...]


def reciprocal_rank_fusion(
    *,
    lexical: tuple[RankedCandidate, ...],
    vector: tuple[RankedCandidate, ...],
    limit: int,
    policy: RetrievalPolicy = HYBRID_RRF_V1,
) -> tuple[SearchEvidence, ...]:
    """Fuse component ranks, rejecting ambiguous or inconsistent evidence."""

    if limit < 1:
        raise ValueError("result limit must be positive")
    if len(lexical) > policy.lexical_candidate_depth:
        raise ValueError("lexical candidates exceed the policy depth")
    if len(vector) > policy.vector_candidate_depth:
        raise ValueError("vector candidates exceed the policy depth")

    component_maps: list[dict[UUID, RankedCandidate]] = []
    for candidates in (lexical, vector):
        by_id: dict[UUID, RankedCandidate] = {}
        for expected_rank, candidate in enumerate(candidates, start=1):
            if candidate.rank != expected_rank:
                raise ValueError("component ranks must be contiguous and ordered")
            evidence_id = candidate.evidence.evidence_id
            if evidence_id in by_id:
                raise ValueError("component candidates must have unique evidence IDs")
            by_id[evidence_id] = candidate
        component_maps.append(by_id)

    lexical_by_id, vector_by_id = component_maps
    fused: list[tuple[float, UUID, EvidenceChunk, int | None, int | None]] = []
    for evidence_id in lexical_by_id.keys() | vector_by_id.keys():
        lexical_candidate = lexical_by_id.get(evidence_id)
        vector_candidate = vector_by_id.get(evidence_id)
        if (
            lexical_candidate is not None
            and vector_candidate is not None
            and lexical_candidate.evidence != vector_candidate.evidence
        ):
            raise ValueError("component candidates disagree about stored evidence")
        if lexical_candidate is not None:
            evidence = lexical_candidate.evidence
        elif vector_candidate is not None:
            evidence = vector_candidate.evidence
        else:  # pragma: no cover - the ID came from the union of component keys
            raise AssertionError("fused evidence must exist in one component")
        lexical_rank = lexical_candidate.rank if lexical_candidate is not None else None
        vector_rank = vector_candidate.rank if vector_candidate is not None else None
        score = sum(
            1.0 / (policy.rrf_constant + rank)
            for rank in (lexical_rank, vector_rank)
            if rank is not None
        )
        if not isfinite(score):
            raise ValueError("RRF score must be finite")
        fused.append((score, evidence_id, evidence, lexical_rank, vector_rank))

    fused.sort(key=lambda item: (-item[0], item[1].int))
    return tuple(
        SearchEvidence(
            rank=rank,
            evidence=item[2],
            lexical_rank=item[3],
            vector_rank=item[4],
            rrf_score=item[0],
        )
        for rank, item in enumerate(fused[:limit], start=1)
    )
