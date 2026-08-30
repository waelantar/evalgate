"""EG-005 real PostgreSQL 18/pgvector retrieval acceptance tests."""

from __future__ import annotations

import asyncio
import math
import os
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from evalgate.adapters.bundled_corpus import (
    CHUNKING_POLICY_SHA256,
    CHUNKING_VERSION,
    LEXICAL_CONFIG_SHA256,
    chunk_declared_corpus,
    load_declared_corpus_by_key,
)
from evalgate.adapters.fastembed_reference import FastEmbedReferenceEmbedding
from evalgate.adapters.postgres_ingestion import PostgresCorpusRepository
from evalgate.adapters.postgres_search import PostgresSearchRepository
from evalgate.application.ingestion import ingest_declared_corpus
from evalgate.application.search import SearchRequest, search_corpus
from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingRole,
    EmbeddingVector,
    ProviderIdentity,
    ProviderMode,
)
from evalgate.domain.search import HYBRID_RRF_V1, RetrievalMode
from evalgate.entrypoints.retrieval_runtime import REFERENCE_MANIFEST, database_event_loop

API_ROOT = Path(__file__).parents[2]
pytestmark = pytest.mark.integration

CORPUS_ID = UUID("10000000-0000-0000-0000-000000000001")
INDEX_ID = UUID("20000000-0000-0000-0000-000000000001")
OTHER_INDEX_ID = UUID("20000000-0000-0000-0000-000000000002")
DOCUMENT_ID = UUID("30000000-0000-0000-0000-000000000001")
SHA = "a" * 64


def _upgrade(database_url: str) -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _vector(first: float, second: float) -> str:
    return "[" + ",".join([str(first), str(second), *(["0"] * 382)]) + "]"


def _seed(database_url: str) -> None:
    _upgrade(database_url)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO corpus_versions "
                "(id, corpus_key, version, manifest_sha256, created_at) "
                "VALUES (:id, 'corpus', '1.0.0', :sha, now())"
            ),
            {"id": CORPUS_ID, "sha": SHA},
        )
        for index_id, key in ((INDEX_ID, "index-one"), (OTHER_INDEX_ID, "index-two")):
            connection.execute(
                text(
                    "INSERT INTO index_versions "
                    "(id, corpus_version_id, index_key, chunking_version, "
                    "chunking_policy_sha256, lexical_config_sha256, embedding_model, "
                    "embedding_revision, embedding_checksum, embedding_dimension, created_at) "
                    "VALUES (:id, :corpus, :key, 'h2-v1', :sha, :lexical, "
                    "'model', 'r1', :sha, 384, now())"
                ),
                {
                    "id": index_id,
                    "corpus": CORPUS_ID,
                    "key": key,
                    "sha": SHA,
                    "lexical": HYBRID_RRF_V1.lexical_config_sha256,
                },
            )
        connection.execute(
            text(
                "INSERT INTO documents "
                "(id, corpus_version_id, source_key, title, license_id, content_sha256, metadata) "
                "VALUES (:id, :corpus, 'source', 'Stored title', 'CC0-1.0', :sha, "
                "CAST(:metadata AS jsonb))"
            ),
            {
                "id": DOCUMENT_ID,
                "corpus": CORPUS_ID,
                "sha": SHA,
                "metadata": '{"provenance":"Original fictional corpus"}',
            },
        )
        rows = (
            (UUID(int=101), INDEX_ID, 0, "alpha alpha alpha", _vector(1, 0)),
            (UUID(int=102), INDEX_ID, 1, "alpha", _vector(1, 0)),
            (UUID(int=103), INDEX_ID, 2, "tieonly", _vector(0, 1)),
            (UUID(int=104), INDEX_ID, 3, "tieonly", _vector(0, 1)),
            (UUID(int=201), OTHER_INDEX_ID, 0, "alpha alpha alpha alpha", _vector(1, 0)),
        )
        for evidence_id, index_id, ordinal, content, vector in rows:
            start = ordinal * 100
            connection.execute(
                text(
                    "INSERT INTO chunks "
                    "(id, corpus_version_id, index_version_id, document_id, ordinal, "
                    "section_key, source_start, source_end, content, content_sha256, "
                    "token_count, search_vector, embedding_384) VALUES "
                    "(:id, :corpus, :index, :document, :ordinal, :section, :start, :end, "
                    ":content, :sha, 1, to_tsvector('pg_catalog.simple', :content), "
                    "CAST(:vector AS vector(384)))"
                ),
                {
                    "id": evidence_id,
                    "corpus": CORPUS_ID,
                    "index": index_id,
                    "document": DOCUMENT_ID,
                    "ordinal": ordinal,
                    "section": f"section-{ordinal}",
                    "start": start,
                    "end": start + len(content),
                    "content": content,
                    "sha": SHA,
                    "vector": vector,
                },
            )
    engine.dispose()


class _Embedding:
    identity = ProviderIdentity(ProviderMode.REFERENCE, "reference", "r1")
    dimension = 384
    model = "model"
    revision = "r1"
    checksum = SHA

    def token_count(self, texts: Sequence[str]) -> int:
        return 1

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
        return (EmbeddingVector((1.0, 0.0) + (0.0,) * 382, self.identity),)


def test_real_postgres_component_ranking_fusion_and_isolation(database_url: str) -> None:
    _seed(database_url)

    async def exercise() -> None:
        engine = create_async_engine(database_url)
        repository = PostgresSearchRepository(engine)
        try:
            selected = await repository.resolve_index(INDEX_ID)
            assert selected is not None
            assert selected.corpus_version_id == CORPUS_ID
            assert selected.index_key == "index-one"
            assert await repository.resolve_index(UUID(int=999)) is None

            lexical = await repository.lexical_candidates(
                index_version=INDEX_ID, query="alpha", depth=50
            )
            assert [item.evidence.evidence_id for item in lexical] == [UUID(int=101), UUID(int=102)]
            assert [item.rank for item in lexical] == [1, 2]
            assert all(item.evidence.evidence_id != UUID(int=201) for item in lexical)

            no_match = await repository.lexical_candidates(
                index_version=INDEX_ID, query="notpresent", depth=50
            )
            assert no_match == ()
            lexical_tie = await repository.lexical_candidates(
                index_version=INDEX_ID, query="tieonly", depth=50
            )
            assert [item.evidence.evidence_id for item in lexical_tie] == [
                UUID(int=103),
                UUID(int=104),
            ]

            vector = await repository.vector_candidates(
                index_version=INDEX_ID,
                embedding=(1.0, 0.0) + (0.0,) * 382,
                depth=50,
            )
            assert [item.evidence.evidence_id for item in vector[:2]] == [
                UUID(int=101),
                UUID(int=102),
            ]
            assert [item.rank for item in vector] == [1, 2, 3, 4]
            assert all(item.evidence.evidence_id != UUID(int=201) for item in vector)
            assert vector[0].evidence.title == "Stored title"
            assert vector[0].evidence.provenance == "Original fictional corpus"

            hybrid = await search_corpus(
                request=SearchRequest("alpha", INDEX_ID, limit=4),
                embedding=_Embedding(),
                repository=repository,
            )
            assert [item.evidence.evidence_id for item in hybrid.evidence[:2]] == [
                UUID(int=101),
                UUID(int=102),
            ]
            assert hybrid.evidence[0].rrf_score == pytest.approx(2 / 61)
            assert hybrid.evidence[1].rrf_score == pytest.approx(2 / 62)
        finally:
            await engine.dispose()

    asyncio.run(exercise(), loop_factory=database_event_loop)


def _reference_snapshot() -> Path:
    value = os.getenv("EVALGATE_REFERENCE_EMBEDDING_SNAPSHOT")
    if value is None or not Path(value).is_dir():
        if os.getenv("EVALGATE_REQUIRE_REFERENCE_TESTS") == "1":
            pytest.fail("required retrieval test has no verified snapshot")
        pytest.skip("EVALGATE_REFERENCE_EMBEDDING_SNAPSHOT is required")
    return Path(value)


def test_governed_reference_index_is_stable_with_finite_exact_latency(database_url: str) -> None:
    snapshot = _reference_snapshot()
    _upgrade(database_url)
    embedding = FastEmbedReferenceEmbedding.from_verified_snapshot(
        manifest_path=REFERENCE_MANIFEST, snapshot_path=snapshot
    )
    corpus = load_declared_corpus_by_key("northstar-operations")
    chunked = chunk_declared_corpus(corpus, tokenizer=embedding)
    sync_engine = create_engine(database_url)
    report = asyncio.run(
        ingest_declared_corpus(
            corpus=chunked.corpus,
            chunks=chunked.chunks,
            embedding=embedding,
            repository=PostgresCorpusRepository(sync_engine),
            chunking_version=CHUNKING_VERSION,
            chunking_policy_sha256=CHUNKING_POLICY_SHA256,
            lexical_config_sha256=LEXICAL_CONFIG_SHA256,
        ),
        loop_factory=database_event_loop,
    )
    sync_engine.dispose()
    assert report.document_count == 20
    assert report.chunk_count == 161

    async def exercise() -> None:
        engine = create_async_engine(database_url)
        repository = PostgresSearchRepository(engine)
        try:
            request = SearchRequest(
                "status ledger recovery",
                report.index_version_id,
                limit=10,
                mode=RetrievalMode.HYBRID,
            )
            first = await search_corpus(request=request, embedding=embedding, repository=repository)
            repeated = await search_corpus(
                request=request, embedding=embedding, repository=repository
            )
            assert [item.evidence.evidence_id for item in first.evidence] == [
                item.evidence.evidence_id for item in repeated.evidence
            ]
            query_vector = (
                await embedding.embed(
                    (EmbeddingInput("status ledger recovery", EmbeddingRole.QUERY),)
                )
            )[0].values
            started = perf_counter()
            exact = await repository.vector_candidates(
                index_version=report.index_version_id,
                embedding=query_vector,
                depth=HYBRID_RRF_V1.vector_candidate_depth,
            )
            observed_ms = (perf_counter() - started) * 1_000
            assert len(exact) == 50
            assert math.isfinite(observed_ms) and observed_ms >= 0
        finally:
            await engine.dispose()

    asyncio.run(exercise(), loop_factory=database_event_loop)
