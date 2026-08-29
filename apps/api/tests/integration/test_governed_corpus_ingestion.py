"""EG-004 migration-backed acceptance tests for immutable corpus ingestion."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import create_engine, text

from evalgate.adapters.bundled_corpus import (
    CHUNKING_POLICY_SHA256,
    CHUNKING_VERSION,
    LEXICAL_CONFIG_SHA256,
    chunk_declared_corpus,
    corpus_version_id,
    load_declared_corpus_by_key,
)
from evalgate.adapters.postgres_ingestion import PostgresCorpusRepository
from evalgate.application.provider_configuration import EmbeddingMode, GenerationMode
from evalgate.config import Settings
from evalgate.domain.corpus import (
    CorpusChunk,
    DeclaredCorpus,
    IngestionError,
    IngestionErrorCode,
    IngestionReport,
)
from evalgate.entrypoints.ingestion import ingest

API_ROOT = Path(__file__).parents[2]
pytestmark = pytest.mark.integration


class _Tokenizer:
    def token_count(self, texts: list[str]) -> int:
        return len(texts[0].split())


def _upgrade(database_url: str) -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _reference_snapshot() -> str:
    value = os.getenv("EVALGATE_REFERENCE_EMBEDDING_SNAPSHOT")
    if value is None or not Path(value).is_dir():
        if os.getenv("EVALGATE_REQUIRE_REFERENCE_TESTS") == "1":
            pytest.fail("required reference-ingestion test has no verified snapshot")
        pytest.skip("EVALGATE_REFERENCE_EMBEDDING_SNAPSHOT is required")
    return str(Path(value).resolve())


def _ingest(
    repository: PostgresCorpusRepository, *, checksum: str = "a" * 64
) -> tuple[DeclaredCorpus, tuple[CorpusChunk, ...], IngestionReport]:
    corpus = load_declared_corpus_by_key("northstar-operations")
    chunks = chunk_declared_corpus(corpus, tokenizer=_Tokenizer()).chunks
    report = repository.ingest(
        corpus=corpus,
        chunks=chunks,
        vectors=tuple((0.0,) * 384 for _ in chunks),
        chunking_version=CHUNKING_VERSION,
        chunking_policy_sha256=CHUNKING_POLICY_SHA256,
        lexical_config_sha256=LEXICAL_CONFIG_SHA256,
        embedding_model="reviewed-runtime",
        embedding_revision="r1",
        embedding_checksum=checksum,
        embedding_dimension=384,
    )
    return corpus, chunks, report


def test_real_postgresql_idempotency_versions_conflicts_and_rollback(database_url: str) -> None:
    _upgrade(database_url)
    engine = create_engine(database_url)
    repository = PostgresCorpusRepository(engine)
    corpus, chunks, created = _ingest(repository)
    assert created.status == "created"

    _, _, repeated = _ingest(repository)
    assert repeated.status == "already_present"
    assert repeated.index_version_id == created.index_version_id
    prechecked = repository.precheck(
        corpus=corpus,
        chunks=chunks,
        chunking_version=CHUNKING_VERSION,
        chunking_policy_sha256=CHUNKING_POLICY_SHA256,
        lexical_config_sha256=LEXICAL_CONFIG_SHA256,
        embedding_model="reviewed-runtime",
        embedding_revision="r1",
        embedding_checksum="a" * 64,
        embedding_dimension=384,
    )
    assert prechecked is not None
    assert prechecked.status == "already_present"

    _, _, changed_index = _ingest(repository, checksum="b" * 64)
    assert changed_index.status == "created"
    assert changed_index.index_version_id != created.index_version_id
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM corpus_versions")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM index_versions")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM documents")).scalar_one() == 20
        assert (
            connection.execute(text("SELECT count(*) FROM chunks")).scalar_one() == len(chunks) * 2
        )

    changed_content = corpus.documents[0].content.replace("fictional", "synthetic", 1)
    changed_document = replace(
        corpus.documents[0],
        content=changed_content,
        content_sha256=sha256(changed_content.encode()).hexdigest(),
    )
    content_version = replace(
        corpus,
        version="1.0.1",
        manifest_sha256=sha256(
            b'{"corpus_key":"northstar-operations","version":"1.0.1"}\n'
        ).hexdigest(),
        documents=(changed_document, *corpus.documents[1:]),
    )
    content_chunks = chunk_declared_corpus(content_version, tokenizer=_Tokenizer()).chunks
    content_report = repository.ingest(
        corpus=content_version,
        chunks=content_chunks,
        vectors=tuple((0.0,) * 384 for _ in content_chunks),
        chunking_version=CHUNKING_VERSION,
        chunking_policy_sha256=CHUNKING_POLICY_SHA256,
        lexical_config_sha256=LEXICAL_CONFIG_SHA256,
        embedding_model="reviewed-runtime",
        embedding_revision="r1",
        embedding_checksum="a" * 64,
        embedding_dimension=384,
    )
    assert content_report.status == "created"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM corpus_versions")).scalar_one() == 2
        assert connection.execute(
            text("SELECT count(*) FROM chunks WHERE index_version_id = :id"),
            {"id": created.index_version_id},
        ).scalar_one() == len(chunks)

    with engine.begin() as connection:
        connection.execute(
            text("UPDATE index_versions SET embedding_revision = 'tampered' WHERE id = :id"),
            {"id": changed_index.index_version_id},
        )
    with pytest.raises(IngestionError) as tampered_index:
        repository.precheck(
            corpus=corpus,
            chunks=chunks,
            chunking_version=CHUNKING_VERSION,
            chunking_policy_sha256=CHUNKING_POLICY_SHA256,
            lexical_config_sha256=LEXICAL_CONFIG_SHA256,
            embedding_model="reviewed-runtime",
            embedding_revision="r1",
            embedding_checksum="b" * 64,
            embedding_dimension=384,
        )
    assert tampered_index.value.code is IngestionErrorCode.PERSISTENCE_FAILED
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE index_versions SET embedding_revision = 'r1' WHERE id = :id"),
            {"id": changed_index.index_version_id},
        )

    first_document = corpus.documents[0]
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE documents SET title = 'tampered' "
                "WHERE corpus_version_id = :corpus_id AND source_key = :source_key"
            ),
            {"corpus_id": created.corpus_version_id, "source_key": first_document.source_key},
        )
    with pytest.raises(IngestionError) as tampered_document:
        repository.precheck(
            corpus=corpus,
            chunks=chunks,
            chunking_version=CHUNKING_VERSION,
            chunking_policy_sha256=CHUNKING_POLICY_SHA256,
            lexical_config_sha256=LEXICAL_CONFIG_SHA256,
            embedding_model="reviewed-runtime",
            embedding_revision="r1",
            embedding_checksum="a" * 64,
            embedding_dimension=384,
        )
    assert tampered_document.value.code is IngestionErrorCode.PERSISTENCE_FAILED
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE documents SET title = :title "
                "WHERE corpus_version_id = :corpus_id AND source_key = :source_key"
            ),
            {
                "title": first_document.title,
                "corpus_id": created.corpus_version_id,
                "source_key": first_document.source_key,
            },
        )

    with engine.connect() as connection:
        connection.execute(
            text("UPDATE chunks SET content = 'tampered' WHERE index_version_id = :id"),
            {"id": created.index_version_id},
        )
        connection.commit()
    with pytest.raises(IngestionError) as tampered:
        _ingest(repository)
    assert tampered.value.code is IngestionErrorCode.PERSISTENCE_FAILED
    assert "tampered" not in str(tampered.value)

    conflicting = replace(corpus, manifest_sha256="f" * 64)
    with pytest.raises(IngestionError) as conflict:
        repository.ingest(
            corpus=conflicting,
            chunks=chunks,
            vectors=tuple((0.0,) * 384 for _ in chunks),
            chunking_version=CHUNKING_VERSION,
            chunking_policy_sha256=CHUNKING_POLICY_SHA256,
            lexical_config_sha256=LEXICAL_CONFIG_SHA256,
            embedding_model="reviewed-runtime",
            embedding_revision="r1",
            embedding_checksum="c" * 64,
            embedding_dimension=384,
        )
    assert conflict.value.code is IngestionErrorCode.PERSISTENCE_FAILED

    rollback_corpus = replace(corpus, corpus_key="northstar-rollback", version="1.0.0")
    rollback_chunks = chunk_declared_corpus(rollback_corpus, tokenizer=_Tokenizer()).chunks
    rollback_id = corpus_version_id(rollback_corpus)
    rollback_ordinal = rollback_chunks[-1].ordinal
    rejection_condition = (
        f"NEW.corpus_version_id = '{rollback_id}' AND NEW.ordinal = {rollback_ordinal}"
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_last_rollback_chunk() RETURNS trigger LANGUAGE plpgsql "
                f"AS $$ BEGIN IF {rejection_condition} "
                "THEN RAISE EXCEPTION 'late insertion failure'; END IF; RETURN NEW; END $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER reject_last_rollback_chunk BEFORE INSERT ON chunks "
                "FOR EACH ROW EXECUTE FUNCTION reject_last_rollback_chunk()"
            )
        )
    with pytest.raises(IngestionError) as failed:
        repository.ingest(
            corpus=rollback_corpus,
            chunks=rollback_chunks,
            vectors=tuple((0.0,) * 384 for _ in rollback_chunks),
            chunking_version=CHUNKING_VERSION,
            chunking_policy_sha256=CHUNKING_POLICY_SHA256,
            lexical_config_sha256=LEXICAL_CONFIG_SHA256,
            embedding_model="reviewed-runtime",
            embedding_revision="r1",
            embedding_checksum="a" * 64,
            embedding_dimension=384,
        )
    assert failed.value.code is IngestionErrorCode.PERSISTENCE_FAILED
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM corpus_versions WHERE corpus_key = 'northstar-rollback'")
            ).scalar_one()
            == 0
        )
    engine.dispose()


def test_real_reference_snapshot_ingests_once_and_prechecks_repeat(database_url: str) -> None:
    snapshot = _reference_snapshot()
    _upgrade(database_url)
    settings = Settings(
        environment="ci",
        database_url=SecretStr(database_url),
        embedding_mode=EmbeddingMode.REFERENCE,
        generation_mode=GenerationMode.DISABLED,
        reference_embedding_snapshot=snapshot,
    )

    first = asyncio.run(ingest(corpus_key="northstar-operations", settings=settings))
    repeated = asyncio.run(ingest(corpus_key="northstar-operations", settings=settings))

    assert first["status"] == "created"
    assert repeated["status"] == "already_present"
    assert first["index_version_id"] == repeated["index_version_id"]
    assert first["document_count"] == 20
    assert first["chunk_count"] == 161

    engine = create_engine(database_url)
    with engine.connect() as connection:
        counts = connection.execute(
            text(
                "SELECT "
                "(SELECT count(*) FROM corpus_versions), "
                "(SELECT count(*) FROM index_versions), "
                "(SELECT count(*) FROM documents), "
                "(SELECT count(*) FROM chunks), "
                "(SELECT min(token_count) FROM chunks), "
                "(SELECT max(token_count) FROM chunks)"
            )
        ).one()
    engine.dispose()
    assert tuple(counts) == (1, 1, 20, 161, 24, 63)
