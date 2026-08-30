"""FastAPI application factory, health/search endpoints, and answer streaming."""

import sys
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Any, Literal, cast
from uuid import UUID, uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from evalgate import __version__
from evalgate.adapters.database import check_database_readiness
from evalgate.adapters.fixtures import DeterministicGroundedAnswerFixture
from evalgate.application.answer import (
    GROUNDED_ANSWER_V1,
    AnswerError,
    AnswerErrorCode,
    AnswerRequest,
)
from evalgate.application.answer_stream import prepare_stream_answer, stream_prepared_answer
from evalgate.application.ports import GenerationPort
from evalgate.application.search import (
    SearchEmbeddingPort,
    SearchError,
    SearchErrorCode,
    SearchRepositoryPort,
    SearchRequest,
    search_corpus,
)
from evalgate.config import Settings, get_settings
from evalgate.domain.answer import AnswerMode
from evalgate.domain.providers import ProviderMode
from evalgate.domain.search import SearchResult
from evalgate.entrypoints.retrieval_runtime import build_reference_retrieval, database_event_loop
from evalgate.entrypoints.sse import HEARTBEAT_FRAME, encode_answer_event


class HealthResponse(BaseModel):
    """Stable health response without sensitive configuration."""

    model_config = ConfigDict(extra="forbid")

    service: Literal["evalgate-api"]
    version: str
    status: Literal["alive", "ready", "not_ready"]
    checks: dict[str, str]


class SearchBody(BaseModel):
    """Strict bounded JSON body for the public search operation."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=1000)
    index_version: UUID
    limit: int = Field(default=10, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_must_contain_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must contain a non-whitespace character")
        return value


class AskBody(BaseModel):
    """Strict bounded request for the frozen POST/fetch/SSE operation."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1000)
    index_version: UUID
    retrieval_limit: int = Field(default=5, ge=1, le=10)
    mode: Literal["fixture"]

    @field_validator("question")
    @classmethod
    def question_must_contain_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must contain a non-whitespace character")
        return value


class EmbeddingIdentityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    revision: str
    checksum: str = Field(pattern="^[a-f0-9]{64}$")
    dimension: Literal[384]


class IndexIdentityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID
    key: str
    chunking_version: str
    chunking_policy_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    lexical_config_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    embedding: EmbeddingIdentityResponse


class CorpusIdentityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID
    key: str
    version: str
    manifest_sha256: str = Field(pattern="^[a-f0-9]{64}$")


class SearchEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    evidence_id: UUID
    document_id: UUID
    source_key: str
    title: str
    license_id: str
    provenance: str
    section_key: str
    source_start: int = Field(ge=0)
    source_end: int = Field(ge=1)
    content: str
    content_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    lexical_rank: int | None = Field(ge=1)
    vector_rank: int | None = Field(ge=1)
    rrf_score: float = Field(gt=0)


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    request_id: UUID
    retrieval_policy: Literal["hybrid-rrf-v1"]
    index: IndexIdentityResponse
    source_corpus: CorpusIdentityResponse
    results: list[SearchEvidenceResponse] = Field(max_length=20)


class ProblemDetails(BaseModel):
    """RFC 9457 response with stable EvalGate extensions."""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: SearchErrorCode
    request_id: UUID


class AskProblemCode(StrEnum):
    """Pre-header ask failures that remain valid Problem Details responses."""

    REQUEST_INVALID = "request.invalid"
    INDEX_NOT_FOUND = "retrieval.index_not_found"
    EMBEDDING_MISMATCH = "retrieval.embedding_mismatch"
    RETRIEVAL_CONFIGURATION_MISMATCH = "retrieval.configuration_mismatch"
    EMBEDDING_UNAVAILABLE = "retrieval.embedding_unavailable"
    DATABASE_UNAVAILABLE = "system.database_unavailable"
    INVALID_EMBEDDING = "retrieval.invalid_embedding"
    INVALID_RESULT = "retrieval.invalid_result"
    MODE_INVALID = "provider.mode_invalid"
    PROVIDER_UNAVAILABLE = "provider.unavailable"
    CONTEXT_INVALID = "answer.context_invalid"


class AskProblemDetails(BaseModel):
    """Content-free RFC 9457 response emitted before SSE headers."""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: AskProblemCode
    request_id: UUID


_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "description": "The search request is invalid."},
    404: {"model": ProblemDetails, "description": "The selected index does not exist."},
    409: {
        "model": ProblemDetails,
        "description": "The retrieval configuration does not match the selected index.",
    },
    500: {
        "model": ProblemDetails,
        "description": "The embedding or ranked retrieval result is invalid.",
    },
    503: {"model": ProblemDetails, "description": "A search dependency is unavailable."},
}

_ERROR_METADATA: dict[SearchErrorCode, tuple[int, str, str]] = {
    SearchErrorCode.REQUEST_INVALID: (400, "Invalid request", "The search request is invalid."),
    SearchErrorCode.INDEX_NOT_FOUND: (
        404,
        "Index not found",
        "The selected index does not exist.",
    ),
    SearchErrorCode.EMBEDDING_MISMATCH: (
        409,
        "Embedding mismatch",
        "The configured embedding does not match the selected index.",
    ),
    SearchErrorCode.RETRIEVAL_CONFIGURATION_MISMATCH: (
        409,
        "Retrieval configuration mismatch",
        "The retrieval policy does not match the selected index.",
    ),
    SearchErrorCode.INVALID_EMBEDDING: (
        500,
        "Invalid embedding",
        "The query embedding result is invalid.",
    ),
    SearchErrorCode.INVALID_RESULT: (
        500,
        "Invalid retrieval result",
        "The ranked retrieval result is invalid.",
    ),
    SearchErrorCode.EMBEDDING_UNAVAILABLE: (
        503,
        "Embedding unavailable",
        "The query embedding service is unavailable.",
    ),
    SearchErrorCode.DATABASE_UNAVAILABLE: (
        503,
        "Database unavailable",
        "The search database is unavailable.",
    ),
}

_ASK_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Ordered UTF-8 SSE answer events.",
        "content": {"text/event-stream": {"schema": {"type": "string"}}},
    },
    400: {"model": AskProblemDetails, "description": "The ask request is invalid."},
    404: {"model": AskProblemDetails, "description": "The selected index does not exist."},
    409: {
        "model": AskProblemDetails,
        "description": "The selected provider or retrieval configuration is incompatible.",
    },
    500: {
        "model": AskProblemDetails,
        "description": "The bounded answer context or retrieval result is invalid.",
    },
    503: {"model": AskProblemDetails, "description": "An ask dependency is unavailable."},
}

_ASK_ERROR_METADATA: dict[AskProblemCode, tuple[int, str, str]] = {
    AskProblemCode.REQUEST_INVALID: (400, "Invalid request", "The ask request is invalid."),
    AskProblemCode.INDEX_NOT_FOUND: (404, "Index not found", "The selected index does not exist."),
    AskProblemCode.EMBEDDING_MISMATCH: (
        409,
        "Embedding mismatch",
        "The configured embedding does not match the selected index.",
    ),
    AskProblemCode.RETRIEVAL_CONFIGURATION_MISMATCH: (
        409,
        "Retrieval configuration mismatch",
        "The retrieval policy does not match the selected index.",
    ),
    AskProblemCode.MODE_INVALID: (
        409,
        "Provider mode invalid",
        "The selected answer provider mode is unavailable.",
    ),
    AskProblemCode.INVALID_EMBEDDING: (
        500,
        "Invalid embedding",
        "The query embedding result is invalid.",
    ),
    AskProblemCode.INVALID_RESULT: (
        500,
        "Invalid retrieval result",
        "The ranked retrieval result is invalid.",
    ),
    AskProblemCode.CONTEXT_INVALID: (
        500,
        "Invalid answer context",
        "The bounded answer context is invalid.",
    ),
    AskProblemCode.EMBEDDING_UNAVAILABLE: (
        503,
        "Embedding unavailable",
        "The query embedding service is unavailable.",
    ),
    AskProblemCode.DATABASE_UNAVAILABLE: (
        503,
        "Database unavailable",
        "The search database is unavailable.",
    ),
    AskProblemCode.PROVIDER_UNAVAILABLE: (
        503,
        "Provider unavailable",
        "The answer provider is unavailable.",
    ),
}


def _build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_recycle=300,
    )


def _problem_response(*, request: Request, request_id: UUID, code: SearchErrorCode) -> JSONResponse:
    status, title, detail = _ERROR_METADATA[code]
    payload = ProblemDetails(
        type=f"urn:evalgate:problem:{code}",
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        code=code,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status,
        content=payload.model_dump(mode="json"),
        media_type="application/problem+json",
    )


def _ask_problem_response(
    *, request: Request, request_id: UUID, code: AskProblemCode
) -> JSONResponse:
    status, title, detail = _ASK_ERROR_METADATA[code]
    payload = AskProblemDetails(
        type=f"urn:evalgate:problem:{code}",
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        code=code,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status,
        content=payload.model_dump(mode="json"),
        media_type="application/problem+json",
    )


def _search_response(result: SearchResult, request_id: UUID) -> SearchResponse:
    if result.policy_id != "hybrid-rrf-v1":
        raise ValueError("HTTP search requires the accepted hybrid retrieval policy")
    index = result.index
    return SearchResponse(
        schema_version="1.0",
        request_id=request_id,
        retrieval_policy=cast(Literal["hybrid-rrf-v1"], result.policy_id),
        index=IndexIdentityResponse(
            version_id=index.index_version_id,
            key=index.index_key,
            chunking_version=index.chunking_version,
            chunking_policy_sha256=index.chunking_policy_sha256,
            lexical_config_sha256=index.lexical_config_sha256,
            embedding=EmbeddingIdentityResponse(
                model=index.embedding_model,
                revision=index.embedding_revision,
                checksum=index.embedding_checksum,
                dimension=384,
            ),
        ),
        source_corpus=CorpusIdentityResponse(
            version_id=index.corpus_version_id,
            key=index.corpus_key,
            version=index.corpus_version,
            manifest_sha256=index.corpus_manifest_sha256,
        ),
        results=[
            SearchEvidenceResponse(
                rank=item.rank,
                evidence_id=item.evidence.evidence_id,
                document_id=item.evidence.document_id,
                source_key=item.evidence.source_key,
                title=item.evidence.title,
                license_id=item.evidence.license_id,
                provenance=item.evidence.provenance,
                section_key=item.evidence.section_key,
                source_start=item.evidence.source_start,
                source_end=item.evidence.source_end,
                content=item.evidence.content,
                content_sha256=item.evidence.content_sha256,
                lexical_rank=item.lexical_rank,
                vector_rank=item.vector_rank,
                rrf_score=item.rrf_score,
            )
            for item in result.evidence
        ],
    )


class _EvalGateApp(FastAPI):
    """FastAPI application with the reviewed Problem Details OpenAPI shape."""

    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is None:
            schema = get_openapi(
                title=self.title,
                version=self.version,
                description=self.description,
                routes=self.routes,
            )
            for path in ("/api/v1/search", "/api/v1/ask"):
                responses = schema["paths"][path]["post"]["responses"]
                responses.pop("422", None)
                for status in ("400", "404", "409", "500", "503"):
                    content = responses[status]["content"]
                    content["application/problem+json"] = content.pop("application/json")
            schema["paths"]["/api/v1/ask"]["post"]["responses"]["200"]["content"].pop(
                "application/json", None
            )
            schemas = schema["components"]["schemas"]
            schemas.pop("HTTPValidationError", None)
            schemas.pop("ValidationError", None)
            self.openapi_schema = schema
        return self.openapi_schema


def create_app(
    settings: Settings | None = None,
    engine: AsyncEngine | None = None,
    *,
    search_repository: SearchRepositoryPort | None = None,
    search_embedding: SearchEmbeddingPort | None = None,
    answer_generation: GenerationPort | None = None,
    request_id_factory: Callable[[], UUID] = uuid4,
) -> FastAPI:
    """Build an application instance with explicit, testable dependencies."""

    resolved_settings = settings or get_settings()
    resolved_engine = engine or _build_engine(resolved_settings)
    if resolved_settings.embedding_mode.value == "reference" and (
        search_repository is None or search_embedding is None
    ):
        default_repository, default_embedding = build_reference_retrieval(
            settings=resolved_settings, engine=resolved_engine
        )
        search_repository = search_repository or default_repository
        search_embedding = search_embedding or default_embedding
    if resolved_settings.generation_mode.value == "fixture" and answer_generation is None:
        answer_generation = DeterministicGroundedAnswerFixture()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await resolved_engine.dispose()

    app = _EvalGateApp(
        title="EvalGate API",
        version=__version__,
        description="Governed retrieval and grounded-answer streaming with operational probes.",
        lifespan=lifespan,
    )
    app.state.database_engine = resolved_engine
    app.state.search_repository = search_repository
    app.state.search_embedding = search_embedding
    app.state.answer_generation = answer_generation

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, _: RequestValidationError) -> JSONResponse:
        if request.url.path == "/api/v1/ask":
            return _ask_problem_response(
                request=request,
                request_id=request_id_factory(),
                code=AskProblemCode.REQUEST_INVALID,
            )
        return _problem_response(
            request=request,
            request_id=request_id_factory(),
            code=SearchErrorCode.REQUEST_INVALID,
        )

    @app.get(
        "/health/live",
        response_model=HealthResponse,
        operation_id="getLiveness",
        response_description="Process is alive.",
        tags=["health"],
    )
    async def liveness() -> HealthResponse:
        return HealthResponse(
            service="evalgate-api",
            version=__version__,
            status="alive",
            checks={},
        )

    @app.get(
        "/health/ready",
        response_model=HealthResponse,
        operation_id="getReadiness",
        response_description="Required foundation dependencies are available.",
        responses={
            503: {
                "model": HealthResponse,
                "description": "A required foundation dependency is unavailable.",
            }
        },
        tags=["health"],
    )
    async def readiness(request: Request) -> HealthResponse | JSONResponse:
        database_engine = cast(AsyncEngine, request.app.state.database_engine)
        state = await check_database_readiness(database_engine)
        payload = HealthResponse(
            service="evalgate-api",
            version=__version__,
            status="ready" if state.ready else "not_ready",
            checks={"database": state.database, "migration": state.migration},
        )
        if not state.ready:
            return JSONResponse(status_code=503, content=payload.model_dump())
        return payload

    @app.post(
        "/api/v1/search",
        response_model=SearchResponse,
        operation_id="searchCorpus",
        response_description="Stable explainable evidence from the selected index.",
        responses=_ERROR_RESPONSES,
        tags=["search"],
    )
    async def search(request: Request, body: SearchBody) -> SearchResponse | JSONResponse:
        request_id = request_id_factory()
        repository = cast(SearchRepositoryPort | None, request.app.state.search_repository)
        embedding = cast(SearchEmbeddingPort | None, request.app.state.search_embedding)
        if repository is None:
            return _problem_response(
                request=request,
                request_id=request_id,
                code=SearchErrorCode.DATABASE_UNAVAILABLE,
            )
        if embedding is None:
            return _problem_response(
                request=request,
                request_id=request_id,
                code=SearchErrorCode.EMBEDDING_UNAVAILABLE,
            )
        try:
            result = await search_corpus(
                request=SearchRequest(
                    query=body.query,
                    index_version=body.index_version,
                    limit=body.limit,
                ),
                embedding=embedding,
                repository=repository,
            )
        except SearchError as error:
            return _problem_response(request=request, request_id=request_id, code=error.code)
        return _search_response(result, request_id)

    @app.post(
        "/api/v1/ask",
        response_model=None,
        operation_id="askCorpus",
        response_description="Ordered UTF-8 SSE answer events.",
        responses=_ASK_ERROR_RESPONSES,
        tags=["answer"],
    )
    async def ask(request: Request, body: AskBody) -> StreamingResponse | JSONResponse:
        request_id = request_id_factory()
        repository = cast(SearchRepositoryPort | None, request.app.state.search_repository)
        embedding = cast(SearchEmbeddingPort | None, request.app.state.search_embedding)
        generation = cast(GenerationPort | None, request.app.state.answer_generation)
        if repository is None:
            return _ask_problem_response(
                request=request,
                request_id=request_id,
                code=AskProblemCode.DATABASE_UNAVAILABLE,
            )
        if embedding is None:
            return _ask_problem_response(
                request=request,
                request_id=request_id,
                code=AskProblemCode.EMBEDDING_UNAVAILABLE,
            )
        if generation is None:
            return _ask_problem_response(
                request=request,
                request_id=request_id,
                code=AskProblemCode.PROVIDER_UNAVAILABLE,
            )
        try:
            if generation.identity.mode is not ProviderMode.FIXTURE:
                return _ask_problem_response(
                    request=request,
                    request_id=request_id,
                    code=AskProblemCode.MODE_INVALID,
                )
        except Exception:
            return _ask_problem_response(
                request=request,
                request_id=request_id,
                code=AskProblemCode.MODE_INVALID,
            )

        try:
            prepared = await prepare_stream_answer(
                request=AnswerRequest(
                    question=body.question,
                    index_version=body.index_version,
                    mode=AnswerMode.FIXTURE,
                    retrieval_limit=body.retrieval_limit,
                ),
                embedding=embedding,
                repository=repository,
                policy=GROUNDED_ANSWER_V1,
            )
        except SearchError as error:
            return _ask_problem_response(
                request=request,
                request_id=request_id,
                code=AskProblemCode(error.code.value),
            )
        except AnswerError as error:
            code = (
                AskProblemCode.REQUEST_INVALID
                if error.code is AnswerErrorCode.REQUEST_INVALID
                else AskProblemCode.CONTEXT_INVALID
            )
            return _ask_problem_response(request=request, request_id=request_id, code=code)

        async def stream_bytes() -> AsyncIterator[bytes]:
            async for event in stream_prepared_answer(
                prepared=prepared,
                generation=generation,
                request_id=request_id,
                is_disconnected=request.is_disconnected,
            ):
                yield HEARTBEAT_FRAME if event is None else encode_answer_event(event)

        return StreamingResponse(
            stream_bytes(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "X-Request-ID": str(request_id),
            },
        )

    return app


def main() -> None:
    """Run the local API without exposing it beyond loopback by default."""

    settings = get_settings()
    loop = database_event_loop if sys.platform == "win32" else "auto"
    uvicorn.run(
        "evalgate.entrypoints.http:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=False,
        loop=cast(Any, loop),
    )
