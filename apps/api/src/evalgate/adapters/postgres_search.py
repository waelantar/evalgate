"""Async PostgreSQL exact lexical and vector retrieval adapter."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from evalgate.application.search import SearchError, SearchErrorCode
from evalgate.domain.search import EvidenceChunk, IndexIdentity, RankedCandidate

_STATEMENT_TIMEOUT_MS = 2_000

_INDEX_SQL = text(
    """
    SELECT
        iv.id AS index_version_id,
        iv.index_key,
        iv.chunking_version,
        iv.chunking_policy_sha256,
        iv.lexical_config_sha256,
        iv.embedding_model,
        iv.embedding_revision,
        iv.embedding_checksum,
        iv.embedding_dimension,
        cv.id AS corpus_version_id,
        cv.corpus_key,
        cv.version AS corpus_version,
        cv.manifest_sha256 AS corpus_manifest_sha256
    FROM index_versions AS iv
    JOIN corpus_versions AS cv ON cv.id = iv.corpus_version_id
    WHERE iv.id = :index_version
    """
)

_LEXICAL_SQL = text(
    """
    WITH selected_index AS (
        SELECT id, corpus_version_id
        FROM index_versions
        WHERE id = :index_version
    ), lexical_query AS (
        SELECT plainto_tsquery('pg_catalog.simple', :query) AS value
    ), ranked AS (
        SELECT
            c.id AS evidence_id,
            c.document_id,
            d.source_key,
            d.title,
            d.license_id,
            d.metadata,
            c.section_key,
            c.source_start,
            c.source_end,
            c.content,
            c.content_sha256,
            row_number() OVER (
                ORDER BY ts_rank_cd(c.search_vector, lexical_query.value) DESC, c.id ASC
            ) AS rank
        FROM selected_index AS selected
        JOIN chunks AS c
          ON c.index_version_id = selected.id
         AND c.corpus_version_id = selected.corpus_version_id
        JOIN documents AS d
          ON d.id = c.document_id
         AND d.corpus_version_id = selected.corpus_version_id
        CROSS JOIN lexical_query
        WHERE c.search_vector @@ lexical_query.value
    )
    SELECT evidence_id, document_id, source_key, title, license_id, metadata,
           section_key, source_start, source_end, content, content_sha256, rank
    FROM ranked
    ORDER BY rank
    LIMIT :depth
    """
)

_VECTOR_SQL = text(
    """
    WITH selected_index AS (
        SELECT id, corpus_version_id
        FROM index_versions
        WHERE id = :index_version
    ), ranked AS (
        SELECT
            c.id AS evidence_id,
            c.document_id,
            d.source_key,
            d.title,
            d.license_id,
            d.metadata,
            c.section_key,
            c.source_start,
            c.source_end,
            c.content,
            c.content_sha256,
            row_number() OVER (
                ORDER BY c.embedding_384 <=> CAST(:embedding AS vector(384)) ASC, c.id ASC
            ) AS rank
        FROM selected_index AS selected
        JOIN chunks AS c
          ON c.index_version_id = selected.id
         AND c.corpus_version_id = selected.corpus_version_id
        JOIN documents AS d
          ON d.id = c.document_id
         AND d.corpus_version_id = selected.corpus_version_id
    )
    SELECT evidence_id, document_id, source_key, title, license_id, metadata,
           section_key, source_start, source_end, content, content_sha256, rank
    FROM ranked
    ORDER BY rank
    LIMIT :depth
    """
)


class PostgresSearchRepository:
    """Search one immutable index with bounded, read-only database work."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def _prepare_read(self, connection: AsyncConnection) -> None:
        await connection.execute(text("SET TRANSACTION READ ONLY"))
        await connection.execute(
            text("SELECT set_config('statement_timeout', :timeout, true)"),
            {"timeout": f"{_STATEMENT_TIMEOUT_MS}ms"},
        )

    async def resolve_index(self, index_version: UUID) -> IndexIdentity | None:
        try:
            async with self._engine.connect() as connection:
                async with connection.begin():
                    await self._prepare_read(connection)
                    row = (
                        (await connection.execute(_INDEX_SQL, {"index_version": index_version}))
                        .mappings()
                        .one_or_none()
                    )
        except SQLAlchemyError as error:
            raise SearchError(
                SearchErrorCode.DATABASE_UNAVAILABLE, "search database is unavailable"
            ) from error
        if row is None:
            return None
        try:
            return IndexIdentity(**dict(row))
        except (KeyError, TypeError, ValueError) as error:
            raise SearchError(
                SearchErrorCode.INVALID_RESULT, "stored index metadata is invalid"
            ) from error

    async def lexical_candidates(
        self, *, index_version: UUID, query: str, depth: int
    ) -> tuple[RankedCandidate, ...]:
        return await self._candidates(
            _LEXICAL_SQL,
            {"index_version": index_version, "query": query, "depth": depth},
        )

    async def vector_candidates(
        self, *, index_version: UUID, embedding: tuple[float, ...], depth: int
    ) -> tuple[RankedCandidate, ...]:
        vector_literal = "[" + ",".join(format(value, ".17g") for value in embedding) + "]"
        return await self._candidates(
            _VECTOR_SQL,
            {
                "index_version": index_version,
                "embedding": vector_literal,
                "depth": depth,
            },
        )

    async def _candidates(
        self, statement: Any, parameters: dict[str, object]
    ) -> tuple[RankedCandidate, ...]:
        try:
            async with self._engine.connect() as connection:
                async with connection.begin():
                    await self._prepare_read(connection)
                    rows = (await connection.execute(statement, parameters)).mappings().all()
        except SQLAlchemyError as error:
            raise SearchError(
                SearchErrorCode.DATABASE_UNAVAILABLE, "search database is unavailable"
            ) from error
        try:
            return tuple(self._candidate(row) for row in rows)
        except (KeyError, TypeError, ValueError) as error:
            raise SearchError(
                SearchErrorCode.INVALID_RESULT, "stored retrieval evidence is invalid"
            ) from error

    @staticmethod
    def _candidate(row: Any) -> RankedCandidate:
        metadata = row["metadata"]
        if not isinstance(metadata, dict) or not isinstance(metadata.get("provenance"), str):
            raise ValueError("stored document provenance is invalid")
        evidence = EvidenceChunk(
            evidence_id=row["evidence_id"],
            document_id=row["document_id"],
            source_key=row["source_key"],
            title=row["title"],
            license_id=row["license_id"],
            provenance=metadata["provenance"],
            section_key=row["section_key"],
            source_start=row["source_start"],
            source_end=row["source_end"],
            content=row["content"],
            content_sha256=row["content_sha256"],
        )
        return RankedCandidate(evidence=evidence, rank=int(row["rank"]))
