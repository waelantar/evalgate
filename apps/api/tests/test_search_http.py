"""HTTP search contract, failure, and privacy tests without PostgreSQL."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from hashlib import sha256
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from evalgate.application.ports import GenerationPort
from evalgate.application.search import SearchEmbeddingPort, SearchRepositoryPort
from evalgate.config import Settings
from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingVector,
    GenerationInput,
    GenerationOutput,
    ProviderIdentity,
    ProviderMode,
)
from evalgate.domain.search import (
    HYBRID_RRF_V1,
    EvidenceChunk,
    IndexIdentity,
    RankedCandidate,
)
from evalgate.entrypoints.http import create_app

SHA = "a" * 64
EVIDENCE_SHA = sha256(b"status evidence").hexdigest()
INDEX_ID = UUID("10000000-0000-0000-0000-000000000001")
CORPUS_ID = UUID("20000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("30000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("40000000-0000-0000-0000-000000000001")
REQUEST_ID = UUID("50000000-0000-0000-0000-000000000001")
IDENTITY = ProviderIdentity(ProviderMode.REFERENCE, "reference", "runtime-r1")


class _Engine:
    async def dispose(self) -> None:
        return None


class _Embedding:
    identity = IDENTITY
    dimension = 384
    model = "reference-model"
    revision = "runtime-r1"
    checksum = SHA

    def token_count(self, texts: Sequence[str]) -> int:
        assert texts
        return 1

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
        assert inputs[0].role.value == "query"
        return (EmbeddingVector((1.0,) + (0.0,) * 383, self.identity),)


class _Repository:
    def __init__(
        self,
        *,
        index: IndexIdentity | None = None,
        include_lexical: bool = True,
        include_vector: bool = True,
    ) -> None:
        self.index = index or _index()
        self.include_lexical = include_lexical
        self.include_vector = include_vector

    async def resolve_index(self, index_version: UUID) -> IndexIdentity | None:
        return self.index if index_version == INDEX_ID else None

    async def lexical_candidates(
        self, *, index_version: UUID, query: str, depth: int
    ) -> tuple[RankedCandidate, ...]:
        assert (index_version, query, depth) == (INDEX_ID, "status ledger", 50)
        return (RankedCandidate(_evidence(), 1),) if self.include_lexical else ()

    async def vector_candidates(
        self, *, index_version: UUID, embedding: tuple[float, ...], depth: int
    ) -> tuple[RankedCandidate, ...]:
        assert index_version == INDEX_ID
        assert len(embedding) == 384
        assert depth == 50
        return (RankedCandidate(_evidence(), 1),) if self.include_vector else ()


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr("postgresql+psycopg://ignored:ignored@localhost/ignored")
    )


def _index(*, lexical_config_sha256: str = HYBRID_RRF_V1.lexical_config_sha256) -> IndexIdentity:
    return IndexIdentity(
        index_version_id=INDEX_ID,
        index_key="northstar-index",
        chunking_version="h2-v1",
        chunking_policy_sha256=SHA,
        lexical_config_sha256=lexical_config_sha256,
        embedding_model="reference-model",
        embedding_revision="runtime-r1",
        embedding_checksum=SHA,
        embedding_dimension=384,
        corpus_version_id=CORPUS_ID,
        corpus_key="northstar-operations",
        corpus_version="1.0.0",
        corpus_manifest_sha256=SHA,
    )


def _evidence() -> EvidenceChunk:
    return EvidenceChunk(
        evidence_id=EVIDENCE_ID,
        document_id=DOCUMENT_ID,
        source_key="status-ledger",
        title="Status Ledger Policy",
        license_id="CC0-1.0",
        provenance="Original fictional corpus",
        section_key="recovery",
        source_start=10,
        source_end=26,
        content="status evidence",
        content_sha256=EVIDENCE_SHA,
    )


def _client(
    *,
    repository: SearchRepositoryPort | None = None,
    embedding: SearchEmbeddingPort | None = None,
    generation: GenerationPort | None = None,
) -> TestClient:
    app = create_app(
        settings=_settings(),
        engine=cast(AsyncEngine, _Engine()),
        search_repository=repository,
        search_embedding=embedding,
        answer_generation=generation,
        request_id_factory=lambda: REQUEST_ID,
    )
    return TestClient(app)


def test_search_success_returns_strict_evidence_and_full_version_identity() -> None:
    with _client(repository=_Repository(), embedding=_Embedding()) as client:
        response = client.post(
            "/api/v1/search",
            json={"query": "status ledger", "index_version": str(INDEX_ID)},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "schema_version": "1.0",
        "request_id": str(REQUEST_ID),
        "retrieval_policy": "hybrid-rrf-v1",
        "index": {
            "version_id": str(INDEX_ID),
            "key": "northstar-index",
            "chunking_version": "h2-v1",
            "chunking_policy_sha256": SHA,
            "lexical_config_sha256": HYBRID_RRF_V1.lexical_config_sha256,
            "embedding": {
                "model": "reference-model",
                "revision": "runtime-r1",
                "checksum": SHA,
                "dimension": 384,
            },
        },
        "source_corpus": {
            "version_id": str(CORPUS_ID),
            "key": "northstar-operations",
            "version": "1.0.0",
            "manifest_sha256": SHA,
        },
        "results": [
            {
                "rank": 1,
                "evidence_id": str(EVIDENCE_ID),
                "document_id": str(DOCUMENT_ID),
                "source_key": "status-ledger",
                "title": "Status Ledger Policy",
                "license_id": "CC0-1.0",
                "provenance": "Original fictional corpus",
                "section_key": "recovery",
                "source_start": 10,
                "source_end": 26,
                "content": "status evidence",
                "content_sha256": EVIDENCE_SHA,
                "lexical_rank": 1,
                "vector_rank": 1,
                "rrf_score": pytest.approx(2 / 61),
            }
        ],
    }


@pytest.mark.parametrize(
    ("repository", "expected_lexical_rank", "expected_vector_rank"),
    [
        (_Repository(include_vector=False), 1, None),
        (_Repository(include_lexical=False), None, 1),
    ],
)
def test_search_serializes_component_only_ranks_as_required_nulls(
    repository: _Repository,
    expected_lexical_rank: int | None,
    expected_vector_rank: int | None,
) -> None:
    with _client(repository=repository, embedding=_Embedding()) as client:
        response = client.post(
            "/api/v1/search",
            json={"query": "status ledger", "index_version": str(INDEX_ID)},
        )

    assert response.status_code == 200
    evidence = response.json()["results"][0]
    assert "lexical_rank" in evidence
    assert "vector_rank" in evidence
    assert evidence["lexical_rank"] == expected_lexical_rank
    assert evidence["vector_rank"] == expected_vector_rank


@pytest.mark.parametrize(
    "body",
    [
        {"query": " ", "index_version": str(INDEX_ID)},
        {"query": "x" * 1001, "index_version": str(INDEX_ID)},
        {"query": "query", "index_version": "not-a-uuid"},
        {"query": "query", "index_version": str(INDEX_ID), "limit": 0},
        {"query": "query", "index_version": str(INDEX_ID), "limit": 21},
        {"query": "query", "index_version": str(INDEX_ID), "unexpected": True},
    ],
)
def test_search_validation_is_problem_json_without_fastapi_422(body: dict[str, object]) -> None:
    with _client(repository=_Repository(), embedding=_Embedding()) as client:
        response = client.post("/api/v1/search", json=body)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "urn:evalgate:problem:request.invalid",
        "title": "Invalid request",
        "status": 400,
        "detail": "The search request is invalid.",
        "instance": "/api/v1/search",
        "code": "request.invalid",
        "request_id": str(REQUEST_ID),
    }
    query = str(body.get("query", ""))
    if query.strip():
        assert query not in response.text


@pytest.mark.parametrize(
    ("repository", "embedding", "status", "code"),
    [
        (None, _Embedding(), 503, "system.database_unavailable"),
        (_Repository(), None, 503, "retrieval.embedding_unavailable"),
        (
            _Repository(index=_index(lexical_config_sha256="b" * 64)),
            _Embedding(),
            409,
            "retrieval.configuration_mismatch",
        ),
    ],
)
def test_search_dependency_and_configuration_failures_are_typed_problem_json(
    repository: SearchRepositoryPort | None,
    embedding: SearchEmbeddingPort | None,
    status: int,
    code: str,
) -> None:
    with _client(repository=repository, embedding=embedding) as client:
        response = client.post(
            "/api/v1/search",
            json={"query": "status ledger", "index_version": str(INDEX_ID)},
        )

    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code
    assert "status ledger" not in response.text


def test_unknown_index_is_not_an_empty_success() -> None:
    with _client(repository=_Repository(), embedding=_Embedding()) as client:
        response = client.post(
            "/api/v1/search",
            json={"query": "status ledger", "index_version": str(UUID(int=999))},
        )

    assert response.status_code == 404
    assert response.json()["code"] == "retrieval.index_not_found"


def test_search_query_and_failure_markers_are_absent_from_logs_and_error_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    marker = "private-query-marker"
    with _client() as client, caplog.at_level("DEBUG"):
        response = client.post(
            "/api/v1/search",
            json={"query": marker, "index_version": str(INDEX_ID)},
        )

    assert response.status_code == 503
    assert marker not in response.text
    assert marker not in caplog.text


def test_openapi_search_has_problem_json_and_no_default_422() -> None:
    app = create_app(settings=_settings(), engine=cast(AsyncEngine, _Engine()))
    operation = app.openapi()["paths"]["/api/v1/search"]["post"]

    assert set(operation["responses"]) == {"200", "400", "404", "409", "500", "503"}
    for status in ("400", "404", "409", "500", "503"):
        assert set(operation["responses"][status]["content"]) == {"application/problem+json"}
    assert "HTTPValidationError" not in app.openapi()["components"]["schemas"]
    assert "ValidationError" not in app.openapi()["components"]["schemas"]
    schemas = app.openapi()["components"]["schemas"]
    required_evidence = schemas["SearchEvidenceResponse"]["required"]
    assert "lexical_rank" in required_evidence
    assert "vector_rank" in required_evidence
    assert schemas["ProblemDetails"]["properties"]["code"] == {
        "$ref": "#/components/schemas/SearchErrorCode"
    }
    assert set(schemas["SearchErrorCode"]["enum"]) == {
        "request.invalid",
        "retrieval.index_not_found",
        "retrieval.embedding_mismatch",
        "retrieval.configuration_mismatch",
        "retrieval.embedding_unavailable",
        "system.database_unavailable",
        "retrieval.invalid_embedding",
        "retrieval.invalid_result",
    }


def _stream_data(response_text: str) -> list[dict[str, object]]:
    frames = [frame for frame in response_text.split("\n\n") if frame and not frame.startswith(":")]
    return [
        cast(
            dict[str, object],
            json.loads(next(line[6:] for line in frame.splitlines() if line.startswith("data: "))),
        )
        for frame in frames
    ]


def test_ask_success_streams_ordered_frames_and_trusted_citation_metadata() -> None:
    with _client(repository=_Repository(), embedding=_Embedding()) as client:
        response = client.post(
            "/api/v1/ask",
            json={
                "question": "status ledger",
                "index_version": str(INDEX_ID),
                "mode": "fixture",
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache, no-transform"
    assert response.headers["x-accel-buffering"] == "no"
    assert response.headers["x-request-id"] == str(REQUEST_ID)
    events = _stream_data(response.text)
    assert [event["type"] for event in events] == [
        "answer.started",
        "retrieval.completed",
        "answer.delta",
        "citations.completed",
        "answer.completed",
    ]
    assert [event["sequence"] for event in events] == [1, 2, 3, 4, 5]
    citation = cast(list[dict[str, object]], events[3]["citations"])[0]
    assert citation["source_key"] == "status-ledger"
    assert citation["quote"] == "status evidence"


@pytest.mark.parametrize(
    "body",
    [
        {"question": " ", "index_version": str(INDEX_ID), "mode": "fixture"},
        {"question": "x" * 1001, "index_version": str(INDEX_ID), "mode": "fixture"},
        {"question": "question", "index_version": "bad", "mode": "fixture"},
        {"question": "question", "index_version": str(INDEX_ID), "mode": "live"},
        {
            "question": "question",
            "index_version": str(INDEX_ID),
            "mode": "fixture",
            "unexpected": True,
        },
    ],
)
def test_ask_validation_is_pre_header_problem_json(body: dict[str, object]) -> None:
    with _client(repository=_Repository(), embedding=_Embedding()) as client:
        response = client.post("/api/v1/ask", json=body)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "request.invalid"
    question = str(body.get("question", ""))
    if question.strip():
        assert question not in response.text


def test_ask_retrieval_failure_is_problem_json_before_stream_headers() -> None:
    with _client(repository=_Repository(), embedding=_Embedding()) as client:
        response = client.post(
            "/api/v1/ask",
            json={
                "question": "private question",
                "index_version": str(UUID(int=999)),
                "mode": "fixture",
            },
        )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "retrieval.index_not_found"
    assert "private question" not in response.text


def test_ask_provider_failure_after_headers_is_terminal_event_without_content() -> None:
    marker = "private-provider-marker"

    class _FailingGeneration:
        identity = ProviderIdentity(ProviderMode.FIXTURE, "failure-fixture", "1")

        async def generate(self, request: GenerationInput) -> GenerationOutput:
            raise RuntimeError(marker)

    with _client(
        repository=_Repository(), embedding=_Embedding(), generation=_FailingGeneration()
    ) as client:
        response = client.post(
            "/api/v1/ask",
            json={
                "question": "status ledger",
                "index_version": str(INDEX_ID),
                "mode": "fixture",
            },
        )

    assert response.status_code == 200
    events = _stream_data(response.text)
    assert [event["type"] for event in events] == [
        "answer.started",
        "retrieval.completed",
        "answer.failed",
    ]
    assert events[-1]["code"] == "provider.unavailable"
    assert marker not in response.text


def test_http_request_cancellation_reaches_and_cleans_up_generation() -> None:
    async def exercise() -> None:
        started = asyncio.Event()
        cleaned = asyncio.Event()

        class _CancellableGeneration:
            identity = ProviderIdentity(ProviderMode.FIXTURE, "cancellable-fixture", "1")

            async def generate(self, request: GenerationInput) -> GenerationOutput:
                started.set()
                try:
                    await asyncio.Event().wait()
                    raise AssertionError("unreachable")
                finally:
                    cleaned.set()

        app = create_app(
            settings=_settings(),
            engine=cast(AsyncEngine, _Engine()),
            search_repository=_Repository(),
            search_embedding=_Embedding(),
            answer_generation=_CancellableGeneration(),
            request_id_factory=lambda: REQUEST_ID,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            request_task = asyncio.create_task(
                client.post(
                    "/api/v1/ask",
                    json={
                        "question": "status ledger",
                        "index_version": str(INDEX_ID),
                        "mode": "fixture",
                    },
                )
            )
            await asyncio.wait_for(started.wait(), timeout=1)
            request_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request_task
            await asyncio.wait_for(cleaned.wait(), timeout=1)

    asyncio.run(exercise())


def test_openapi_ask_freezes_sse_and_pre_header_problem_responses() -> None:
    app = create_app(settings=_settings(), engine=cast(AsyncEngine, _Engine()))
    operation = app.openapi()["paths"]["/api/v1/ask"]["post"]

    assert set(operation["responses"]) == {"200", "400", "404", "409", "500", "503"}
    assert set(operation["responses"]["200"]["content"]) == {"text/event-stream"}
    for status in ("400", "404", "409", "500", "503"):
        assert set(operation["responses"][status]["content"]) == {"application/problem+json"}
    assert "422" not in operation["responses"]
