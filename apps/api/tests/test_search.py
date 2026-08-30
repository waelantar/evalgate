"""Pure retrieval policy and framework-free search-use-case tests."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

import pytest

from evalgate.application.search import (
    MAX_QUERY_CODE_POINTS,
    SearchError,
    SearchErrorCode,
    SearchRequest,
    normalize_query,
    search_corpus,
)
from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingVector,
    ProviderIdentity,
    ProviderMode,
)
from evalgate.domain.search import (
    HYBRID_RRF_V1,
    EvidenceChunk,
    IndexIdentity,
    RankedCandidate,
    RetrievalMode,
    reciprocal_rank_fusion,
)

SHA = "a" * 64
LEXICAL_SHA = HYBRID_RRF_V1.lexical_config_sha256
INDEX_ID = UUID("10000000-0000-0000-0000-000000000001")
CORPUS_ID = UUID("20000000-0000-0000-0000-000000000001")
IDENTITY = ProviderIdentity(ProviderMode.REFERENCE, "reference", "runtime-r1")


def _index(
    *,
    lexical_config_sha256: str = LEXICAL_SHA,
    embedding_revision: str = "runtime-r1",
) -> IndexIdentity:
    return IndexIdentity(
        index_version_id=INDEX_ID,
        index_key="northstar-index",
        chunking_version="h2-v1",
        chunking_policy_sha256=SHA,
        lexical_config_sha256=lexical_config_sha256,
        embedding_model="reference-model",
        embedding_revision=embedding_revision,
        embedding_checksum=SHA,
        embedding_dimension=384,
        corpus_version_id=CORPUS_ID,
        corpus_key="northstar-operations",
        corpus_version="1.0.0",
        corpus_manifest_sha256=SHA,
    )


def _evidence(value: int, *, content: str = "Evidence") -> EvidenceChunk:
    return EvidenceChunk(
        evidence_id=UUID(int=value),
        document_id=UUID(int=100 + value),
        source_key=f"source-{value}",
        title=f"Source {value}",
        license_id="CC0-1.0",
        provenance="Original fictional corpus",
        section_key=f"section-{value}",
        source_start=0,
        source_end=len(content),
        content=content,
        content_sha256=SHA,
    )


class _Embedding:
    identity = IDENTITY
    dimension = 384
    model = "reference-model"
    revision = "runtime-r1"
    checksum = SHA

    def __init__(self, *, tokens: int = 1, values: tuple[float, ...] | None = None) -> None:
        self.tokens = tokens
        self.values = values if values is not None else (1.0,) + (0.0,) * 383
        self.embedded: list[EmbeddingInput] = []

    def token_count(self, texts: Sequence[str]) -> int:
        assert len(texts) == 1
        return self.tokens

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
        self.embedded.extend(inputs)
        return (EmbeddingVector(values=self.values, identity=self.identity),)


class _Repository:
    def __init__(self, *, index: IndexIdentity | None = None) -> None:
        self.index = _index() if index is None else index
        self.lexical_calls: list[tuple[UUID, str, int]] = []
        self.vector_calls: list[tuple[UUID, tuple[float, ...], int]] = []
        self.lexical: tuple[RankedCandidate, ...] = (RankedCandidate(_evidence(1), 1),)
        self.vector: tuple[RankedCandidate, ...] = (RankedCandidate(_evidence(2), 1),)

    async def resolve_index(self, index_version: UUID) -> IndexIdentity | None:
        return self.index if index_version == INDEX_ID else None

    async def lexical_candidates(
        self, *, index_version: UUID, query: str, depth: int
    ) -> tuple[RankedCandidate, ...]:
        self.lexical_calls.append((index_version, query, depth))
        return self.lexical

    async def vector_candidates(
        self, *, index_version: UUID, embedding: tuple[float, ...], depth: int
    ) -> tuple[RankedCandidate, ...]:
        self.vector_calls.append((index_version, embedding, depth))
        return self.vector


def _search_error(call: Any) -> SearchError:
    with pytest.raises(SearchError) as captured:
        asyncio.run(call)
    return captured.value


def test_rrf_fuses_overlap_and_uses_uuid_for_stable_score_ties() -> None:
    first = _evidence(1)
    second = _evidence(2)
    third = _evidence(3)

    result = reciprocal_rank_fusion(
        lexical=(RankedCandidate(second, 1), RankedCandidate(first, 2)),
        vector=(RankedCandidate(third, 1), RankedCandidate(first, 2)),
        limit=3,
    )

    assert [item.evidence.evidence_id for item in result] == [
        first.evidence_id,
        second.evidence_id,
        third.evidence_id,
    ]
    assert result[0].lexical_rank == 2
    assert result[0].vector_rank == 2
    assert result[0].rrf_score == pytest.approx(2 / 62)
    assert result[1].rrf_score == result[2].rrf_score == pytest.approx(1 / 61)
    assert [item.rank for item in result] == [1, 2, 3]


def test_rrf_rejects_noncontiguous_duplicate_or_disagreeing_component_evidence() -> None:
    evidence = _evidence(1)
    with pytest.raises(ValueError, match="contiguous"):
        reciprocal_rank_fusion(lexical=(RankedCandidate(evidence, 2),), vector=(), limit=1)
    with pytest.raises(ValueError, match="unique"):
        reciprocal_rank_fusion(
            lexical=(RankedCandidate(evidence, 1), RankedCandidate(evidence, 2)),
            vector=(),
            limit=2,
        )
    changed = EvidenceChunk(
        evidence_id=evidence.evidence_id,
        document_id=evidence.document_id,
        source_key=evidence.source_key,
        title=evidence.title,
        license_id=evidence.license_id,
        provenance=evidence.provenance,
        section_key=evidence.section_key,
        source_start=evidence.source_start,
        source_end=9,
        content="Different",
        content_sha256=evidence.content_sha256,
    )
    with pytest.raises(ValueError, match="disagree"):
        reciprocal_rank_fusion(
            lexical=(RankedCandidate(evidence, 1),),
            vector=(RankedCandidate(changed, 1),),
            limit=1,
        )


def test_rrf_rejects_component_lists_beyond_the_policy_depth() -> None:
    oversized = tuple(RankedCandidate(_evidence(rank), rank) for rank in range(1, 52))

    with pytest.raises(ValueError, match="lexical candidates exceed"):
        reciprocal_rank_fusion(lexical=oversized, vector=(), limit=1)
    with pytest.raises(ValueError, match="vector candidates exceed"):
        reciprocal_rank_fusion(lexical=(), vector=oversized, limit=1)


def test_query_normalization_and_code_point_bounds() -> None:
    assert normalize_query("  Cafe\u0301\r\npolicy  ") == "Caf\u00e9\npolicy"
    assert normalize_query("x" * MAX_QUERY_CODE_POINTS) == "x" * MAX_QUERY_CODE_POINTS
    for invalid in (" \r\n\t ", "x" * (MAX_QUERY_CODE_POINTS + 1)):
        with pytest.raises(SearchError) as captured:
            normalize_query(invalid)
        assert captured.value.code is SearchErrorCode.REQUEST_INVALID


@pytest.mark.parametrize(
    ("mode", "expected_lexical", "expected_vector", "expected_embeds"),
    [
        (RetrievalMode.LEXICAL, 1, 0, 0),
        (RetrievalMode.VECTOR, 0, 1, 1),
        (RetrievalMode.HYBRID, 1, 1, 1),
    ],
)
def test_search_modes_call_only_the_selected_components(
    mode: RetrievalMode,
    expected_lexical: int,
    expected_vector: int,
    expected_embeds: int,
) -> None:
    embedding = _Embedding()
    repository = _Repository()

    result = asyncio.run(
        search_corpus(
            request=SearchRequest(" query ", INDEX_ID, mode=mode),
            embedding=embedding,
            repository=repository,
        )
    )

    assert len(repository.lexical_calls) == expected_lexical
    assert len(repository.vector_calls) == expected_vector
    assert len(embedding.embedded) == expected_embeds
    assert result.policy_id == "hybrid-rrf-v1"
    assert result.index == _index()
    assert repository.lexical_calls == [] or repository.lexical_calls[0][1:] == ("query", 50)
    assert repository.vector_calls == [] or repository.vector_calls[0][2] == 50


@pytest.mark.parametrize("mode", list(RetrievalMode))
def test_token_cap_applies_to_every_mode_before_candidate_queries(mode: RetrievalMode) -> None:
    repository = _Repository()
    error = _search_error(
        search_corpus(
            request=SearchRequest("query", INDEX_ID, mode=mode),
            embedding=_Embedding(tokens=513),
            repository=repository,
        )
    )

    assert error.code is SearchErrorCode.REQUEST_INVALID
    assert repository.lexical_calls == []
    assert repository.vector_calls == []


def test_invalid_token_count_is_a_typed_provider_result_failure() -> None:
    error = _search_error(
        search_corpus(
            request=SearchRequest("query", INDEX_ID),
            embedding=_Embedding(tokens=0),
            repository=_Repository(),
        )
    )
    assert error.code is SearchErrorCode.INVALID_EMBEDDING


def test_search_rejects_policy_and_embedding_identity_mismatches_before_queries() -> None:
    wrong_lexical = _Repository(index=_index(lexical_config_sha256="b" * 64))
    error = _search_error(
        search_corpus(
            request=SearchRequest("query", INDEX_ID),
            embedding=_Embedding(),
            repository=wrong_lexical,
        )
    )
    assert error.code is SearchErrorCode.RETRIEVAL_CONFIGURATION_MISMATCH
    assert wrong_lexical.lexical_calls == []
    assert wrong_lexical.vector_calls == []

    wrong_embedding = _Repository(index=_index(embedding_revision="other"))
    error = _search_error(
        search_corpus(
            request=SearchRequest("query", INDEX_ID),
            embedding=_Embedding(),
            repository=wrong_embedding,
        )
    )
    assert error.code is SearchErrorCode.EMBEDDING_MISMATCH
    assert wrong_embedding.lexical_calls == []
    assert wrong_embedding.vector_calls == []

    class _InconsistentIdentityEmbedding(_Embedding):
        identity = ProviderIdentity(ProviderMode.REFERENCE, "reference", "different-revision")

    error = _search_error(
        search_corpus(
            request=SearchRequest("query", INDEX_ID),
            embedding=_InconsistentIdentityEmbedding(),
            repository=_Repository(),
        )
    )
    assert error.code is SearchErrorCode.EMBEDDING_MISMATCH


@pytest.mark.parametrize("values", [(0.0,) * 384, (1.0,) * 383, (1e308,) * 384])
def test_search_rejects_zero_norm_wrong_width_or_overflowing_vectors(
    values: tuple[float, ...],
) -> None:
    repository = _Repository()
    error = _search_error(
        search_corpus(
            request=SearchRequest("query", INDEX_ID),
            embedding=_Embedding(values=values),
            repository=repository,
        )
    )
    assert error.code is SearchErrorCode.INVALID_EMBEDDING
    assert repository.lexical_calls == []
    assert repository.vector_calls == []


@pytest.mark.parametrize("output", [None, object(), (), (object(),)])
def test_search_rejects_every_malformed_provider_output_shape_and_redacts_failures(
    output: object,
) -> None:
    class _InvalidEmbedding(_Embedding):
        async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
            del inputs
            return cast(tuple[EmbeddingVector, ...], output)

    error = _search_error(
        search_corpus(
            request=SearchRequest("secret-query-marker", INDEX_ID),
            embedding=_InvalidEmbedding(),
            repository=_Repository(),
        )
    )
    assert error.code is SearchErrorCode.INVALID_EMBEDDING
    assert "secret-query-marker" not in str(error)


@pytest.mark.parametrize("output", [None, object(), (object(),)])
def test_search_rejects_every_malformed_candidate_output_shape_and_redacts_failures(
    output: object,
) -> None:
    class _MalformedRepository(_Repository):
        async def lexical_candidates(
            self, *, index_version: UUID, query: str, depth: int
        ) -> tuple[RankedCandidate, ...]:
            del index_version, query, depth
            return cast(tuple[RankedCandidate, ...], output)

    error = _search_error(
        search_corpus(
            request=SearchRequest("private-query-marker", INDEX_ID),
            embedding=_Embedding(),
            repository=_MalformedRepository(),
        )
    )

    assert error.code is SearchErrorCode.INVALID_RESULT
    assert "private-query-marker" not in str(error)


def test_search_maps_oversized_repository_component_to_invalid_result() -> None:
    repository = _Repository()
    repository.lexical = tuple(RankedCandidate(_evidence(rank), rank) for rank in range(1, 52))

    error = _search_error(
        search_corpus(
            request=SearchRequest("private-query-marker", INDEX_ID),
            embedding=_Embedding(),
            repository=repository,
        )
    )

    assert error.code is SearchErrorCode.INVALID_RESULT
    assert "private-query-marker" not in str(error)


def test_unknown_index_and_repository_failure_are_distinct_and_redacted() -> None:
    error = _search_error(
        search_corpus(
            request=SearchRequest("query", UUID(int=999)),
            embedding=_Embedding(),
            repository=_Repository(),
        )
    )
    assert error.code is SearchErrorCode.INDEX_NOT_FOUND

    class _BrokenRepository(_Repository):
        async def resolve_index(self, index_version: UUID) -> IndexIdentity | None:
            del index_version
            raise RuntimeError("database-secret-marker")

    error = _search_error(
        search_corpus(
            request=SearchRequest("query", INDEX_ID),
            embedding=_Embedding(),
            repository=_BrokenRepository(),
        )
    )
    assert error.code is SearchErrorCode.DATABASE_UNAVAILABLE
    assert "database-secret-marker" not in str(error)


def test_malformed_repository_ranks_are_typed_and_redacted() -> None:
    repository = _Repository()
    repository.lexical = (RankedCandidate(_evidence(1), 2),)

    error = _search_error(
        search_corpus(
            request=SearchRequest("private-query-marker", INDEX_ID),
            embedding=_Embedding(),
            repository=repository,
        )
    )

    assert error.code is SearchErrorCode.INVALID_RESULT
    assert "private-query-marker" not in str(error)
