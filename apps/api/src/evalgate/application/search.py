"""Framework-free explainable search use case and outbound ports."""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import UUID

from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingRole,
    EmbeddingVector,
    ProviderIdentity,
    ProviderMode,
)
from evalgate.domain.search import (
    HYBRID_RRF_V1,
    IndexIdentity,
    RankedCandidate,
    RetrievalMode,
    RetrievalPolicy,
    SearchResult,
    reciprocal_rank_fusion,
)

MAX_QUERY_CODE_POINTS = 1000
MAX_QUERY_TOKENS = 512
MIN_RESULT_LIMIT = 1
MAX_RESULT_LIMIT = 20
DEFAULT_RESULT_LIMIT = 10


class SearchErrorCode(StrEnum):
    """Stable, content-free search failure categories."""

    REQUEST_INVALID = "request.invalid"
    INDEX_NOT_FOUND = "retrieval.index_not_found"
    EMBEDDING_MISMATCH = "retrieval.embedding_mismatch"
    RETRIEVAL_CONFIGURATION_MISMATCH = "retrieval.configuration_mismatch"
    EMBEDDING_UNAVAILABLE = "retrieval.embedding_unavailable"
    DATABASE_UNAVAILABLE = "system.database_unavailable"
    INVALID_EMBEDDING = "retrieval.invalid_embedding"
    INVALID_RESULT = "retrieval.invalid_result"


class SearchError(RuntimeError):
    """Typed search failure whose message must never include request content."""

    def __init__(self, code: SearchErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """Provider-neutral bounded search input."""

    query: str
    index_version: UUID
    limit: int = DEFAULT_RESULT_LIMIT
    mode: RetrievalMode = RetrievalMode.HYBRID


@runtime_checkable
class SearchEmbeddingPort(Protocol):
    """Pinned reference query embedding and tokenizer identity."""

    @property
    def identity(self) -> ProviderIdentity: ...

    @property
    def dimension(self) -> int: ...

    @property
    def model(self) -> str: ...

    @property
    def revision(self) -> str: ...

    @property
    def checksum(self) -> str: ...

    def token_count(self, texts: Sequence[str]) -> int: ...

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]: ...


@runtime_checkable
class SearchRepositoryPort(Protocol):
    """Retrieve independently ranked candidates from one selected stored index."""

    async def resolve_index(self, index_version: UUID) -> IndexIdentity | None: ...

    async def lexical_candidates(
        self, *, index_version: UUID, query: str, depth: int
    ) -> tuple[RankedCandidate, ...]: ...

    async def vector_candidates(
        self, *, index_version: UUID, embedding: tuple[float, ...], depth: int
    ) -> tuple[RankedCandidate, ...]: ...


def normalize_query(query: str) -> str:
    """Apply the reviewed lossless line-ending/Unicode policy and outer trim."""

    if len(query) > MAX_QUERY_CODE_POINTS:
        raise SearchError(SearchErrorCode.REQUEST_INVALID, "search request is invalid")
    normalized = unicodedata.normalize("NFC", query.replace("\r\n", "\n").replace("\r", "\n"))
    normalized = normalized.strip()
    if not normalized:
        raise SearchError(SearchErrorCode.REQUEST_INVALID, "search request is invalid")
    return normalized


def _validate_request(request: SearchRequest) -> str:
    if not MIN_RESULT_LIMIT <= request.limit <= MAX_RESULT_LIMIT:
        raise SearchError(SearchErrorCode.REQUEST_INVALID, "search request is invalid")
    return normalize_query(request.query)


def _embedding_matches(index: IndexIdentity, embedding: SearchEmbeddingPort) -> bool:
    return (
        embedding.identity.mode is ProviderMode.REFERENCE
        and embedding.identity.revision == embedding.revision
        and embedding.model == index.embedding_model
        and embedding.revision == index.embedding_revision
        and embedding.checksum == index.embedding_checksum
        and embedding.dimension == index.embedding_dimension == 384
    )


def _retrieval_policy_matches(index: IndexIdentity, policy: RetrievalPolicy) -> bool:
    return index.lexical_config_sha256 == policy.lexical_config_sha256


def _validate_embedding_output(output: object, embedding: SearchEmbeddingPort) -> tuple[float, ...]:
    """Validate untrusted adapter output without exposing its values in an error."""

    if not isinstance(output, Sequence) or isinstance(output, (str, bytes)) or len(output) != 1:
        raise ValueError("embedding output must contain exactly one vector")
    embedded_vector = output[0]
    if not isinstance(embedded_vector, EmbeddingVector):
        raise ValueError("embedding output has an invalid vector type")
    if embedded_vector.identity != embedding.identity:
        raise ValueError("embedding output identity does not match its adapter")
    values = embedded_vector.values
    if len(values) != 384 or any(not math.isfinite(value) for value in values):
        raise ValueError("embedding output values are invalid")
    vector_norm = math.hypot(*values)
    if not math.isfinite(vector_norm) or vector_norm == 0:
        raise ValueError("embedding output norm is invalid")
    return values


def _validate_candidates(output: object, *, component: str) -> tuple[RankedCandidate, ...]:
    """Copy one adapter candidate sequence after validating its public element type."""

    if not isinstance(output, Sequence) or isinstance(output, (str, bytes)):
        raise ValueError(f"{component} candidates must be a sequence")
    candidates: list[RankedCandidate] = []
    for candidate in output:
        if not isinstance(candidate, RankedCandidate):
            raise ValueError(f"{component} candidates contain an invalid item")
        candidates.append(candidate)
    return tuple(candidates)


async def search_corpus(
    *,
    request: SearchRequest,
    embedding: SearchEmbeddingPort,
    repository: SearchRepositoryPort,
    policy: RetrievalPolicy = HYBRID_RRF_V1,
) -> SearchResult:
    """Search one immutable index and return stable explainable evidence."""

    query = _validate_request(request)
    try:
        index = await repository.resolve_index(request.index_version)
    except SearchError:
        raise
    except Exception as error:
        raise SearchError(
            SearchErrorCode.DATABASE_UNAVAILABLE, "search database is unavailable"
        ) from error
    if index is None:
        raise SearchError(SearchErrorCode.INDEX_NOT_FOUND, "selected index was not found")
    if not _retrieval_policy_matches(index, policy):
        raise SearchError(
            SearchErrorCode.RETRIEVAL_CONFIGURATION_MISMATCH,
            "retrieval policy does not match the selected index",
        )
    try:
        embedding_matches = _embedding_matches(index, embedding)
    except Exception as error:
        raise SearchError(
            SearchErrorCode.EMBEDDING_UNAVAILABLE,
            "query embedding identity is unavailable",
        ) from error
    if not embedding_matches:
        raise SearchError(
            SearchErrorCode.EMBEDDING_MISMATCH,
            "configured embedding does not match the selected index",
        )

    try:
        token_count = embedding.token_count((query,))
        if token_count > MAX_QUERY_TOKENS:
            raise SearchError(SearchErrorCode.REQUEST_INVALID, "search request is invalid")
        if token_count < 1:
            raise SearchError(
                SearchErrorCode.INVALID_EMBEDDING,
                "query tokenizer returned an invalid count",
            )
    except SearchError:
        raise
    except Exception as error:
        raise SearchError(
            SearchErrorCode.EMBEDDING_UNAVAILABLE,
            "query tokenizer is unavailable",
        ) from error

    vector: tuple[float, ...] | None = None
    if request.mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
        try:
            embedded = await embedding.embed((EmbeddingInput(query, EmbeddingRole.QUERY),))
        except SearchError:
            raise
        except Exception as error:
            raise SearchError(
                SearchErrorCode.EMBEDDING_UNAVAILABLE,
                "query embedding is unavailable",
            ) from error
        try:
            vector = _validate_embedding_output(embedded, embedding)
        except Exception as error:
            raise SearchError(
                SearchErrorCode.INVALID_EMBEDDING,
                "query embedding returned an invalid vector",
            ) from error

    try:
        lexical = (
            await repository.lexical_candidates(
                index_version=index.index_version_id,
                query=query,
                depth=policy.lexical_candidate_depth,
            )
            if request.mode in (RetrievalMode.LEXICAL, RetrievalMode.HYBRID)
            else ()
        )
        if request.mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
            if vector is None:
                raise SearchError(
                    SearchErrorCode.INVALID_EMBEDDING,
                    "query embedding returned an invalid vector",
                )
            vector_candidates = await repository.vector_candidates(
                index_version=index.index_version_id,
                embedding=vector,
                depth=policy.vector_candidate_depth,
            )
        else:
            vector_candidates = ()
    except SearchError:
        raise
    except Exception as error:
        raise SearchError(
            SearchErrorCode.DATABASE_UNAVAILABLE, "search database is unavailable"
        ) from error

    try:
        lexical = _validate_candidates(lexical, component="lexical")
        vector_candidates = _validate_candidates(vector_candidates, component="vector")
        evidence = reciprocal_rank_fusion(
            lexical=lexical,
            vector=vector_candidates,
            limit=request.limit,
            policy=policy,
        )
    except Exception as error:
        raise SearchError(
            SearchErrorCode.INVALID_RESULT,
            "retrieval returned invalid ranked evidence",
        ) from error
    return SearchResult(policy_id=policy.policy_id, index=index, evidence=evidence)
