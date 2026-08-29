"""PostgreSQL implementation of the atomic declared-corpus ingestion port."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from evalgate.adapters.bundled_corpus import corpus_version_id, document_id
from evalgate.domain.corpus import (
    CorpusChunk,
    DeclaredCorpus,
    IngestionError,
    IngestionErrorCode,
    IngestionReport,
)


def _index_key(
    *,
    corpus: DeclaredCorpus,
    chunking_version: str,
    chunking_policy_sha256: str,
    lexical_config_sha256: str,
    embedding_model: str,
    embedding_revision: str,
    embedding_checksum: str,
    embedding_dimension: int,
) -> str:
    identity = ":".join(
        (
            chunking_version,
            chunking_policy_sha256,
            lexical_config_sha256,
            embedding_model,
            embedding_revision,
            embedding_checksum,
            str(embedding_dimension),
        )
    )
    return "-".join(
        (
            corpus.corpus_key,
            corpus.version,
            sha256(identity.encode()).hexdigest()[:24],
        )
    )


class PostgresCorpusRepository:
    """Persist immutable corpus evidence with transaction-scoped idempotency locking."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def precheck(
        self,
        *,
        corpus: DeclaredCorpus,
        chunks: Sequence[CorpusChunk],
        chunking_version: str,
        chunking_policy_sha256: str,
        lexical_config_sha256: str,
        embedding_model: str,
        embedding_revision: str,
        embedding_checksum: str,
        embedding_dimension: int,
    ) -> IngestionReport | None:
        """Read-only exact-repeat check; the transaction rechecks before writing."""

        corpus_id = corpus_version_id(corpus)
        index_key = _index_key(
            corpus=corpus,
            chunking_version=chunking_version,
            chunking_policy_sha256=chunking_policy_sha256,
            lexical_config_sha256=lexical_config_sha256,
            embedding_model=embedding_model,
            embedding_revision=embedding_revision,
            embedding_checksum=embedding_checksum,
            embedding_dimension=embedding_dimension,
        )
        index_id = uuid5(NAMESPACE_URL, f"urn:evalgate:index:{corpus_id}:{index_key}")
        try:
            with self._engine.connect() as connection:
                existing = connection.execute(
                    text(
                        "SELECT corpus_version_id, index_key, chunking_version, "
                        "chunking_policy_sha256, lexical_config_sha256, embedding_model, "
                        "embedding_revision, embedding_checksum, embedding_dimension "
                        "FROM index_versions WHERE id = :id"
                    ),
                    {"id": index_id},
                ).one_or_none()
                if existing is None:
                    return None
                stored_corpus = connection.execute(
                    text(
                        "SELECT id, manifest_sha256 FROM corpus_versions "
                        "WHERE corpus_key = :key AND version = :version"
                    ),
                    {"key": corpus.corpus_key, "version": corpus.version},
                ).one_or_none()
                stored_documents = connection.execute(
                    text(
                        "SELECT id, source_key, title, license_id, content_sha256, metadata "
                        "FROM documents WHERE corpus_version_id = :id"
                    ),
                    {"id": corpus_id},
                ).all()
                stored = connection.execute(
                    text(
                        "SELECT id, document_id, ordinal, section_key, content_sha256, token_count, "
                        "source_start, source_end, content FROM chunks WHERE index_version_id = :id"
                    ),
                    {"id": index_id},
                ).all()
        except SQLAlchemyError as error:
            raise IngestionError(
                IngestionErrorCode.PERSISTENCE_FAILED,
                "declared corpus ingestion could not be checked",
            ) from error
        expected_index = (
            corpus_id,
            index_key,
            chunking_version,
            chunking_policy_sha256,
            lexical_config_sha256,
            embedding_model,
            embedding_revision,
            embedding_checksum,
            embedding_dimension,
        )
        actual_index = (
            existing.corpus_version_id,
            existing.index_key,
            existing.chunking_version,
            existing.chunking_policy_sha256,
            existing.lexical_config_sha256,
            existing.embedding_model,
            existing.embedding_revision,
            existing.embedding_checksum,
            existing.embedding_dimension,
        )
        expected_documents = {
            (
                document_id(corpus, document),
                document.source_key,
                document.title,
                document.license_id,
                document.content_sha256,
                json.dumps({"provenance": document.provenance}, sort_keys=True),
            )
            for document in corpus.documents
        }
        actual_documents = {
            (
                row.id,
                row.source_key,
                row.title,
                row.license_id,
                row.content_sha256,
                json.dumps(row.metadata, sort_keys=True),
            )
            for row in stored_documents
        }
        expected = {
            (
                uuid5(
                    index_id,
                    f"chunk:{chunk.document_id}:{chunk.ordinal}:{chunk.content_sha256}",
                ),
                chunk.document_id,
                chunk.ordinal,
                chunk.section_key,
                chunk.content_sha256,
                chunk.token_count,
                chunk.source_start,
                chunk.source_end,
                chunk.content,
            )
            for chunk in chunks
        }
        actual = {
            (
                row.id,
                row.document_id,
                row.ordinal,
                row.section_key,
                row.content_sha256,
                row.token_count,
                row.source_start,
                row.source_end,
                row.content,
            )
            for row in stored
        }
        if (
            stored_corpus is None
            or stored_corpus.id != corpus_id
            or stored_corpus.manifest_sha256 != corpus.manifest_sha256
            or actual_index != expected_index
            or actual_documents != expected_documents
            or actual != expected
        ):
            raise IngestionError(
                IngestionErrorCode.PERSISTENCE_FAILED,
                "stored index conflicts with immutable evidence",
            )
        return IngestionReport(
            corpus_version_id=corpus_id,
            index_version_id=index_id,
            corpus_key=corpus.corpus_key,
            corpus_version=corpus.version,
            document_count=len(corpus.documents),
            chunk_count=len(chunks),
            status="already_present",
        )

    def ingest(
        self,
        *,
        corpus: DeclaredCorpus,
        chunks: Sequence[CorpusChunk],
        vectors: Sequence[tuple[float, ...]],
        chunking_version: str,
        chunking_policy_sha256: str,
        lexical_config_sha256: str,
        embedding_model: str,
        embedding_revision: str,
        embedding_checksum: str,
        embedding_dimension: int,
    ) -> IngestionReport:
        """Store all evidence or no evidence; an exact repeat is a no-op report."""

        if len(chunks) != len(vectors):
            raise IngestionError(
                IngestionErrorCode.PERSISTENCE_FAILED, "ingestion batch is invalid"
            )
        corpus_id = corpus_version_id(corpus)
        index_key = _index_key(
            corpus=corpus,
            chunking_version=chunking_version,
            chunking_policy_sha256=chunking_policy_sha256,
            lexical_config_sha256=lexical_config_sha256,
            embedding_model=embedding_model,
            embedding_revision=embedding_revision,
            embedding_checksum=embedding_checksum,
            embedding_dimension=embedding_dimension,
        )
        index_id = uuid5(NAMESPACE_URL, f"urn:evalgate:index:{corpus_id}:{index_key}")
        lock_key = str(corpus_id)
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                    {"lock_key": lock_key},
                )
                existing = connection.execute(
                    text(
                        "SELECT corpus_version_id, index_key, chunking_version, chunking_policy_sha256, lexical_config_sha256, embedding_model, embedding_revision, embedding_checksum, embedding_dimension FROM index_versions WHERE id = :id"
                    ),
                    {"id": index_id},
                ).one_or_none()
                if existing is not None:
                    expected_index = (
                        corpus_id,
                        index_key,
                        chunking_version,
                        chunking_policy_sha256,
                        lexical_config_sha256,
                        embedding_model,
                        embedding_revision,
                        embedding_checksum,
                        embedding_dimension,
                    )
                    actual_index = (
                        existing.corpus_version_id,
                        existing.index_key,
                        existing.chunking_version,
                        existing.chunking_policy_sha256,
                        existing.lexical_config_sha256,
                        existing.embedding_model,
                        existing.embedding_revision,
                        existing.embedding_checksum,
                        existing.embedding_dimension,
                    )
                    stored_corpus = connection.execute(
                        text(
                            "SELECT id, manifest_sha256 FROM corpus_versions "
                            "WHERE corpus_key = :key AND version = :version"
                        ),
                        {"key": corpus.corpus_key, "version": corpus.version},
                    ).one_or_none()
                    stored_documents = connection.execute(
                        text(
                            "SELECT id, source_key, title, license_id, content_sha256, metadata "
                            "FROM documents WHERE corpus_version_id = :id"
                        ),
                        {"id": corpus_id},
                    ).all()
                    expected_documents = {
                        (
                            document_id(corpus, document),
                            document.source_key,
                            document.title,
                            document.license_id,
                            document.content_sha256,
                            json.dumps({"provenance": document.provenance}, sort_keys=True),
                        )
                        for document in corpus.documents
                    }
                    actual_documents = {
                        (
                            row.id,
                            row.source_key,
                            row.title,
                            row.license_id,
                            row.content_sha256,
                            json.dumps(row.metadata, sort_keys=True),
                        )
                        for row in stored_documents
                    }
                    chunk_count = connection.execute(
                        text("SELECT count(*) FROM chunks WHERE index_version_id = :id"),
                        {"id": index_id},
                    ).scalar_one()
                    stored_chunks = connection.execute(
                        text(
                            "SELECT id, document_id, ordinal, section_key, source_start, source_end, content, "
                            "content_sha256, token_count FROM chunks WHERE index_version_id = :id"
                        ),
                        {"id": index_id},
                    ).all()
                    expected_chunks = {
                        (
                            uuid5(
                                index_id,
                                f"chunk:{chunk.document_id}:{chunk.ordinal}:{chunk.content_sha256}",
                            ),
                            chunk.document_id,
                            chunk.ordinal,
                            chunk.section_key,
                            chunk.source_start,
                            chunk.source_end,
                            chunk.content,
                            chunk.content_sha256,
                            chunk.token_count,
                        )
                        for chunk in chunks
                    }
                    actual_chunks = {
                        (
                            row.id,
                            row.document_id,
                            row.ordinal,
                            row.section_key,
                            row.source_start,
                            row.source_end,
                            row.content,
                            row.content_sha256,
                            row.token_count,
                        )
                        for row in stored_chunks
                    }
                    if (
                        stored_corpus is None
                        or stored_corpus.id != corpus_id
                        or stored_corpus.manifest_sha256 != corpus.manifest_sha256
                        or actual_documents != expected_documents
                        or actual_chunks != expected_chunks
                        or actual_index != expected_index
                        or chunk_count != len(chunks)
                    ):
                        raise IngestionError(
                            IngestionErrorCode.PERSISTENCE_FAILED,
                            "stored index conflicts with immutable evidence",
                        )
                    return IngestionReport(
                        corpus_version_id=corpus_id,
                        index_version_id=index_id,
                        corpus_key=corpus.corpus_key,
                        corpus_version=corpus.version,
                        document_count=len(corpus.documents),
                        chunk_count=len(chunks),
                        status="already_present",
                    )
                now = datetime.now(UTC)
                connection.execute(
                    text(
                        "INSERT INTO corpus_versions (id, corpus_key, version, manifest_sha256, created_at) "
                        "VALUES (:id, :key, :version, :manifest_sha256, :created_at) "
                        "ON CONFLICT (corpus_key, version) DO NOTHING"
                    ),
                    {
                        "id": corpus_id,
                        "key": corpus.corpus_key,
                        "version": corpus.version,
                        "manifest_sha256": corpus.manifest_sha256,
                        "created_at": now,
                    },
                )
                stored_corpus = connection.execute(
                    text(
                        "SELECT id, manifest_sha256 FROM corpus_versions WHERE corpus_key = :key AND version = :version"
                    ),
                    {"key": corpus.corpus_key, "version": corpus.version},
                ).one()
                if (
                    stored_corpus.id != corpus_id
                    or stored_corpus.manifest_sha256 != corpus.manifest_sha256
                ):
                    raise IngestionError(
                        IngestionErrorCode.PERSISTENCE_FAILED,
                        "declared corpus version conflicts with immutable stored evidence",
                    )
                connection.execute(
                    text(
                        "INSERT INTO index_versions (id, corpus_version_id, index_key, chunking_version, "
                        "chunking_policy_sha256, lexical_config_sha256, embedding_model, embedding_revision, "
                        "embedding_checksum, embedding_dimension, created_at) VALUES "
                        "(:id, :corpus_id, :index_key, :chunking_version, :chunking_policy_sha256, "
                        ":lexical_config_sha256, :embedding_model, :embedding_revision, :embedding_checksum, "
                        ":embedding_dimension, :created_at)"
                    ),
                    {
                        "id": index_id,
                        "corpus_id": corpus_id,
                        "index_key": index_key,
                        "chunking_version": chunking_version,
                        "chunking_policy_sha256": chunking_policy_sha256,
                        "lexical_config_sha256": lexical_config_sha256,
                        "embedding_model": embedding_model,
                        "embedding_revision": embedding_revision,
                        "embedding_checksum": embedding_checksum,
                        "embedding_dimension": embedding_dimension,
                        "created_at": now,
                    },
                )
                stored_documents = connection.execute(
                    text(
                        "SELECT id, source_key, title, license_id, content_sha256, metadata FROM documents WHERE corpus_version_id = :id"
                    ),
                    {"id": corpus_id},
                ).all()
                if not stored_documents:
                    for document in corpus.documents:
                        connection.execute(
                            text(
                                "INSERT INTO documents (id, corpus_version_id, source_key, title, license_id, "
                                "content_sha256, metadata) VALUES (:id, :corpus_id, :source_key, :title, "
                                ":license_id, :content_sha256, CAST(:metadata AS jsonb))"
                            ),
                            {
                                "id": document_id(corpus, document),
                                "corpus_id": corpus_id,
                                "source_key": document.source_key,
                                "title": document.title,
                                "license_id": document.license_id,
                                "content_sha256": document.content_sha256,
                                "metadata": json.dumps(
                                    {"provenance": document.provenance}, sort_keys=True
                                ),
                            },
                        )
                else:
                    expected_documents = {
                        (
                            document_id(corpus, document),
                            document.source_key,
                            document.title,
                            document.license_id,
                            document.content_sha256,
                            json.dumps({"provenance": document.provenance}, sort_keys=True),
                        )
                        for document in corpus.documents
                    }
                    actual_documents = {
                        (
                            row.id,
                            row.source_key,
                            row.title,
                            row.license_id,
                            row.content_sha256,
                            json.dumps(row.metadata, sort_keys=True),
                        )
                        for row in stored_documents
                    }
                    if actual_documents != expected_documents:
                        raise IngestionError(
                            IngestionErrorCode.PERSISTENCE_FAILED,
                            "stored corpus documents conflict with immutable evidence",
                        )
                for chunk, vector in zip(chunks, vectors, strict=True):
                    chunk_id = uuid5(
                        index_id,
                        f"chunk:{chunk.document_id}:{chunk.ordinal}:{chunk.content_sha256}",
                    )
                    vector_literal = "[" + ",".join(str(value) for value in vector) + "]"
                    connection.execute(
                        text(
                            "INSERT INTO chunks (id, corpus_version_id, index_version_id, document_id, ordinal, "
                            "section_key, source_start, source_end, content, content_sha256, token_count, "
                            "search_vector, embedding_384) VALUES (:id, :corpus_id, :index_id, :document_id, "
                            ":ordinal, :section_key, :source_start, :source_end, :content, :content_sha256, "
                            ":token_count, to_tsvector('pg_catalog.simple', :content), CAST(:embedding AS vector))"
                        ),
                        {
                            "id": chunk_id,
                            "corpus_id": corpus_id,
                            "index_id": index_id,
                            "document_id": chunk.document_id,
                            "ordinal": chunk.ordinal,
                            "section_key": chunk.section_key,
                            "source_start": chunk.source_start,
                            "source_end": chunk.source_end,
                            "content": chunk.content,
                            "content_sha256": chunk.content_sha256,
                            "token_count": chunk.token_count,
                            "embedding": vector_literal,
                        },
                    )
        except IngestionError:
            raise
        except SQLAlchemyError as error:
            raise IngestionError(
                IngestionErrorCode.PERSISTENCE_FAILED,
                "declared corpus ingestion could not be persisted",
            ) from error
        return IngestionReport(
            corpus_version_id=corpus_id,
            index_version_id=index_id,
            corpus_key=corpus.corpus_key,
            corpus_version=corpus.version,
            document_count=len(corpus.documents),
            chunk_count=len(chunks),
            status="created",
        )
