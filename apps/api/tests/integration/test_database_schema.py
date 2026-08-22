"""EG-003 acceptance tests against PostgreSQL 18 and pgvector 0.8.5."""

from __future__ import annotations

import asyncio
import selectors
import sys
from collections.abc import Coroutine
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from evalgate.adapters.database import (
    EXPECTED_ALEMBIC_HEAD,
    DatabaseReadiness,
    check_database_readiness,
)
from evalgate.config import Settings
from evalgate.entrypoints.database import reset_database, seed_empty

API_ROOT = Path(__file__).parents[2]
pytestmark = pytest.mark.integration
EXPECTED_TABLES = {
    "alembic_version",
    "chunks",
    "corpus_versions",
    "documents",
    "eval_case_results",
    "eval_cases",
    "eval_datasets",
    "eval_runs",
    "index_versions",
}


def _run_async[T](coroutine: Coroutine[Any, Any, T]) -> T:
    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())
        ) as runner:
            return runner.run(coroutine)
    return asyncio.run(coroutine)


def _alembic(database_url: str) -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _settings(database_url: str) -> Settings:
    return Settings(environment="ci", database_url=SecretStr(database_url))


def _upgrade(database_url: str) -> None:
    command.upgrade(_alembic(database_url), "head")


def test_upgrade_reaches_one_head_and_installs_reviewed_postgresql_schema(
    database_url: str,
) -> None:
    script = ScriptDirectory.from_config(_alembic(database_url))
    assert script.get_heads() == [EXPECTED_ALEMBIC_HEAD]
    _upgrade(database_url)
    engine = create_engine(database_url)
    with engine.connect() as connection:
        server_major = connection.execute(text("SHOW server_version_num")).scalar_one()
        current_database = connection.execute(text("SELECT current_database()")).scalar_one()
        vector_version = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
        tables = set(
            connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).scalars()
        )
        vector_type = connection.execute(
            text(
                "SELECT format_type(a.atttypid, a.atttypmod) "
                "FROM pg_attribute a "
                "JOIN pg_class c ON c.oid = a.attrelid "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relname = 'chunks' "
                "AND a.attname = 'embedding_384'"
            )
        ).scalar_one()
        search_vector_generation = connection.execute(
            text(
                "SELECT a.attgenerated FROM pg_attribute a "
                "JOIN pg_class c ON c.oid = a.attrelid "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relname = 'chunks' "
                "AND a.attname = 'search_vector'"
            )
        ).scalar_one()
        heads = tuple(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
        constraints = set(
            connection.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE connamespace = 'public'::regnamespace"
                )
            ).scalars()
        )
        foreign_key_delete_actions = set(
            connection.execute(
                text(
                    "SELECT confdeltype FROM pg_constraint "
                    "WHERE connamespace = 'public'::regnamespace AND contype = 'f'"
                )
            ).scalars()
        )
        indexes = set(
            connection.execute(
                text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
            ).scalars()
        )

    engine.dispose()
    assert server_major.startswith("18")
    assert current_database == make_url(database_url).database
    assert current_database.startswith("evalgate_test_")
    assert vector_version == "0.8.5"
    assert EXPECTED_TABLES <= tables
    assert vector_type == "vector(384)"
    assert search_vector_generation == ""
    assert heads == (EXPECTED_ALEMBIC_HEAD,)
    assert foreign_key_delete_actions == {"r"}
    assert {
        "fk_chunks_document_corpus",
        "fk_chunks_index_corpus",
        "fk_eval_case_results_case_dataset",
        "fk_eval_case_results_run_dataset",
        "uq_chunks_index_document_ordinal",
        "uq_documents_corpus_source",
        "uq_eval_case_results_run_case",
    } <= constraints
    assert {
        "ix_chunks_document_corpus",
        "ix_chunks_index_corpus",
        "ix_eval_case_results_case_dataset",
        "ix_eval_case_results_run_dataset",
        "ix_eval_runs_dataset",
        "ix_eval_runs_index",
        "ix_index_versions_corpus",
    } <= indexes


def test_constraints_reject_invalid_dimension_offsets_duplicates_and_cross_corpus_chunk(
    database_url: str,
) -> None:
    _upgrade(database_url)
    engine = create_engine(database_url)
    corpus_a, corpus_b = uuid4(), uuid4()
    index_a, document_a, document_b = uuid4(), uuid4(), uuid4()
    sha = "a" * 64

    with engine.begin() as connection:
        for corpus_id, key in ((corpus_a, "a"), (corpus_b, "b")):
            connection.execute(
                text(
                    "INSERT INTO corpus_versions "
                    "(id, corpus_key, version, manifest_sha256, created_at) "
                    "VALUES (:id, :key, 'v1', :sha, now())"
                ),
                {"id": corpus_id, "key": key, "sha": sha},
            )
        connection.execute(
            text(
                "INSERT INTO index_versions "
                "(id, corpus_version_id, index_key, chunking_version, "
                "chunking_policy_sha256, lexical_config_sha256, embedding_model, "
                "embedding_revision, embedding_checksum, embedding_dimension, created_at) "
                "VALUES (:id, :corpus, 'index-a', 'chunk-v1', :sha, :sha, "
                "'BAAI/bge-small-en-v1.5', 'revision', :sha, 384, now())"
            ),
            {"id": index_a, "corpus": corpus_a, "sha": sha},
        )
        for document_id, corpus_id, source_key in (
            (document_a, corpus_a, "doc-a"),
            (document_b, corpus_b, "doc-b"),
        ):
            connection.execute(
                text(
                    "INSERT INTO documents "
                    "(id, corpus_version_id, source_key, title, license_id, "
                    "content_sha256, metadata) VALUES "
                    "(:id, :corpus, :source, 'Title', 'CC0-1.0', :sha, '{}'::jsonb)"
                ),
                {
                    "id": document_id,
                    "corpus": corpus_id,
                    "source": source_key,
                    "sha": sha,
                },
            )

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO index_versions "
                "(id, corpus_version_id, index_key, chunking_version, "
                "chunking_policy_sha256, lexical_config_sha256, embedding_model, "
                "embedding_revision, embedding_checksum, embedding_dimension, created_at) "
                "VALUES (:id, :corpus, 'bad-width', 'chunk-v1', :sha, :sha, "
                "'model', 'revision', :sha, 383, now())"
            ),
            {"id": uuid4(), "corpus": corpus_a, "sha": sha},
        )

    vector = "[" + ",".join("0" for _ in range(384)) + "]"
    chunk_statement = text(
        "INSERT INTO chunks "
        "(id, corpus_version_id, index_version_id, document_id, ordinal, "
        "section_key, source_start, source_end, content, content_sha256, "
        "token_count, search_vector, embedding_384) VALUES "
        "(:id, :corpus, :index_id, :document, :ordinal, 'section', "
        ":source_start, :source_end, 'content', :sha, 1, "
        "to_tsvector('simple', 'content'), CAST(:vector AS vector))"
    )
    valid_chunk = {
        "id": uuid4(),
        "corpus": corpus_a,
        "index_id": index_a,
        "document": document_a,
        "ordinal": 0,
        "source_start": 0,
        "source_end": 7,
        "sha": sha,
        "vector": vector,
    }
    with engine.begin() as connection:
        connection.execute(chunk_statement, valid_chunk)

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(chunk_statement, {**valid_chunk, "id": uuid4()})

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            chunk_statement,
            {**valid_chunk, "id": uuid4(), "ordinal": 1, "source_start": 4, "source_end": 4},
        )

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            chunk_statement,
            {**valid_chunk, "id": uuid4(), "ordinal": 1, "document": document_b},
        )

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text("DELETE FROM corpus_versions WHERE id = :id"),
            {"id": corpus_a},
        )

    engine.dispose()


def test_case_result_cannot_cross_evaluation_dataset(database_url: str) -> None:
    _upgrade(database_url)
    engine = create_engine(database_url)
    dataset_a, dataset_b = uuid4(), uuid4()
    case_b, run_a = uuid4(), uuid4()
    corpus, index = uuid4(), uuid4()
    sha = "c" * 64
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO corpus_versions "
                "(id, corpus_key, version, manifest_sha256, created_at) "
                "VALUES (:id, 'corpus', 'v1', :sha, now())"
            ),
            {"id": corpus, "sha": sha},
        )
        connection.execute(
            text(
                "INSERT INTO index_versions "
                "(id, corpus_version_id, index_key, chunking_version, "
                "chunking_policy_sha256, lexical_config_sha256, embedding_model, "
                "embedding_revision, embedding_checksum, embedding_dimension, created_at) "
                "VALUES (:id, :corpus, 'index', 'chunk-v1', :sha, :sha, "
                "'model', 'revision', :sha, 384, now())"
            ),
            {"id": index, "corpus": corpus, "sha": sha},
        )
        for dataset_id, version in ((dataset_a, "a"), (dataset_b, "b")):
            connection.execute(
                text(
                    "INSERT INTO eval_datasets "
                    "(id, version, manifest_sha256, review_status) "
                    "VALUES (:id, :version, :sha, 'reviewed')"
                ),
                {"id": dataset_id, "version": version, "sha": sha},
            )
        connection.execute(
            text(
                "INSERT INTO eval_cases "
                "(id, dataset_id, stable_key, split, question, answerable, "
                "reference_evidence, tags) VALUES "
                "(:id, :dataset, 'case', 'regression', 'Question?', true, '[]', '[]')"
            ),
            {"id": case_b, "dataset": dataset_b},
        )
        connection.execute(
            text(
                "INSERT INTO eval_runs "
                "(id, run_key, index_version_id, eval_dataset_id, mode, status, "
                "code_sha, version_manifest, artifact_sha256) VALUES "
                "(:id, 'run', :index_id, :dataset, 'retrieval', 'complete', "
                ":code_sha, '{}'::jsonb, :artifact_sha)"
            ),
            {
                "id": run_a,
                "index_id": index,
                "dataset": dataset_a,
                "code_sha": "d" * 40,
                "artifact_sha": sha,
            },
        )

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO eval_case_results "
                "(id, eval_dataset_id, eval_run_id, eval_case_id, retrieval_evidence, "
                "citation_evidence, metric_values, status) VALUES "
                "(:id, :dataset, :run_id, :case_id, '{}', '{}', '{}', 'complete')"
            ),
            {"id": uuid4(), "dataset": dataset_a, "run_id": run_a, "case_id": case_b},
        )
    engine.dispose()


def test_repeated_upgrade_and_readiness_require_exact_head(database_url: str) -> None:
    _upgrade(database_url)
    _upgrade(database_url)

    async def probe() -> tuple[DatabaseReadiness, DatabaseReadiness]:
        engine = create_async_engine(database_url)
        current = await check_database_readiness(engine)
        await engine.dispose()
        sync_engine = create_engine(database_url)
        with sync_engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = 'unexpected'"))
        sync_engine.dispose()
        engine = create_async_engine(database_url)
        mismatch = await check_database_readiness(engine)
        await engine.dispose()
        return current, mismatch

    current, mismatch = _run_async(probe())
    assert current.ready
    assert current.migration == "current"
    assert not mismatch.ready
    assert mismatch.database == "available"
    assert mismatch.migration == "mismatch"


def test_seed_empty_and_confirmed_reset_restore_empty_ready_database(database_url: str) -> None:
    settings = _settings(database_url)
    seed_empty(settings)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO corpus_versions "
                "(id, corpus_key, version, manifest_sha256, created_at) "
                "VALUES (:id, 'temporary', 'v1', :sha, now())"
            ),
            {"id": uuid4(), "sha": "b" * 64},
        )
    engine.dispose()

    reset_database(settings, confirmed=True)

    engine = create_engine(database_url)
    with engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM corpus_versions")).scalar_one()
        head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        vector_version = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
    engine.dispose()

    async def probe() -> DatabaseReadiness:
        async_engine = create_async_engine(database_url)
        result = await check_database_readiness(async_engine)
        await async_engine.dispose()
        return result

    readiness = _run_async(probe())
    assert count == 0
    assert head == EXPECTED_ALEMBIC_HEAD
    assert vector_version == "0.8.5"
    assert readiness.ready
