"""Focused structural and row-validation tests for PostgreSQL search."""

import asyncio
from types import TracebackType
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from evalgate.adapters import postgres_search
from evalgate.application.search import SearchError, SearchErrorCode
from evalgate.domain.search import RankedCandidate


def _row() -> dict[str, object]:
    return {
        "evidence_id": UUID(int=1),
        "document_id": UUID(int=2),
        "source_key": "source",
        "title": "Title",
        "license_id": "CC0-1.0",
        "metadata": {"provenance": "Original fictional corpus"},
        "section_key": "section",
        "source_start": 0,
        "source_end": 7,
        "content": "content",
        "content_sha256": "a" * 64,
        "rank": 1,
    }


def test_queries_bind_private_values_and_pin_exact_reviewed_operators() -> None:
    lexical = str(postgres_search._LEXICAL_SQL)
    vector = str(postgres_search._VECTOR_SQL)

    assert "plainto_tsquery('pg_catalog.simple', :query)" in lexical
    assert "@@ lexical_query.value" in lexical
    assert "ts_rank_cd" in lexical
    assert "DESC, c.id ASC" in lexical
    assert "<=> CAST(:embedding AS vector(384)) ASC, c.id ASC" in vector
    assert ":index_version" in lexical and ":index_version" in vector
    assert "c.corpus_version_id = selected.corpus_version_id" in lexical
    assert "c.corpus_version_id = selected.corpus_version_id" in vector
    assert "HNSW" not in vector.upper()


def test_row_mapping_reconstructs_provenance_without_raw_scores() -> None:
    candidate = postgres_search.PostgresSearchRepository._candidate(_row())

    assert isinstance(candidate, RankedCandidate)
    assert candidate.rank == 1
    assert candidate.evidence.provenance == "Original fictional corpus"
    assert not hasattr(candidate, "score")


@pytest.mark.parametrize("metadata", [{}, {"provenance": 123}, "private-content"])
def test_row_mapping_rejects_invalid_provenance(metadata: object) -> None:
    row = _row()
    row["metadata"] = metadata

    with pytest.raises(ValueError, match="stored document provenance is invalid"):
        postgres_search.PostgresSearchRepository._candidate(row)


class _Result:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def mappings(self) -> "_Result":
        return self

    def all(self) -> list[dict[str, object]]:
        return self.rows


class _Transaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback


class _Connection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def begin(self) -> _Transaction:
        return _Transaction()

    async def execute(
        self, statement: object, parameters: dict[str, object] | None = None
    ) -> _Result:
        del parameters
        return _Result(self.rows if "FROM ranked" in str(statement) else [])


class _ConnectionContext:
    def __init__(self, rows: list[dict[str, object]], failure: Exception | None = None) -> None:
        self.rows = rows
        self.failure = failure

    async def __aenter__(self) -> _Connection:
        if self.failure is not None:
            raise self.failure
        return _Connection(self.rows)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback


class _Engine:
    def __init__(self, rows: list[dict[str, object]], failure: Exception | None = None) -> None:
        self.rows = rows
        self.failure = failure

    def connect(self) -> _ConnectionContext:
        return _ConnectionContext(self.rows, self.failure)


def test_corrupt_row_is_translated_to_content_free_typed_error() -> None:
    row = _row()
    row["metadata"] = {"provenance": "private-row-marker"}
    row["content_sha256"] = "invalid-private-row-marker"
    repository = postgres_search.PostgresSearchRepository(cast(AsyncEngine, _Engine([row])))

    with pytest.raises(SearchError) as captured:
        asyncio.run(
            repository.lexical_candidates(index_version=UUID(int=1), query="query", depth=1)
        )

    assert captured.value.code is SearchErrorCode.INVALID_RESULT
    assert "private-row-marker" not in str(captured.value)


def test_database_failure_is_translated_to_content_free_typed_error() -> None:
    repository = postgres_search.PostgresSearchRepository(
        cast(AsyncEngine, _Engine([], SQLAlchemyError("private-database-marker")))
    )

    with pytest.raises(SearchError) as captured:
        asyncio.run(
            repository.lexical_candidates(index_version=UUID(int=1), query="query", depth=1)
        )

    assert captured.value.code is SearchErrorCode.DATABASE_UNAVAILABLE
    assert "private-database-marker" not in str(captured.value)
