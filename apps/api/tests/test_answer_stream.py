"""Ordered answer-stream, retry, heartbeat, backpressure, and cancellation tests."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from evalgate.adapters.fixtures import DeterministicGroundedAnswerFixture
from evalgate.application.answer import (
    GROUNDED_ANSWER_V1,
    AnswerRequest,
    PreparedAnswer,
)
from evalgate.application.answer_stream import prepare_stream_answer, stream_prepared_answer
from evalgate.application.search import SearchError, SearchErrorCode
from evalgate.domain.answer import AnswerMode
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
    SearchEvidence,
)
from evalgate.domain.stream import AnswerStreamEvent, AnswerStreamEventType
from evalgate.entrypoints.sse import HEARTBEAT_FRAME, encode_answer_event

INDEX_ID = UUID("10000000-0000-0000-0000-000000000001")
CORPUS_ID = UUID("20000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("30000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("40000000-0000-0000-0000-000000000001")
REQUEST_ID = UUID("50000000-0000-0000-0000-000000000001")
SHA = "a" * 64
EMBEDDING_IDENTITY = ProviderIdentity(ProviderMode.REFERENCE, "reference", "runtime-r1")
FIXTURE_IDENTITY = ProviderIdentity(ProviderMode.FIXTURE, "fixture", "1")
REPOSITORY_ROOT = Path(__file__).parents[3]


def _index() -> IndexIdentity:
    return IndexIdentity(
        index_version_id=INDEX_ID,
        index_key="northstar-index",
        chunking_version="h2-v1",
        chunking_policy_sha256=SHA,
        lexical_config_sha256=HYBRID_RRF_V1.lexical_config_sha256,
        embedding_model="reference",
        embedding_revision="runtime-r1",
        embedding_checksum=SHA,
        embedding_dimension=384,
        corpus_version_id=CORPUS_ID,
        corpus_key="northstar-operations",
        corpus_version="1.0.0",
        corpus_manifest_sha256=SHA,
    )


def _chunk(content: str = "status evidence") -> EvidenceChunk:
    return EvidenceChunk(
        evidence_id=EVIDENCE_ID,
        document_id=DOCUMENT_ID,
        source_key="status-ledger",
        title="Status Ledger Policy",
        license_id="CC0-1.0",
        provenance="Original fictional corpus",
        section_key="recovery",
        source_start=10,
        source_end=10 + len(content),
        content=content,
        content_sha256=sha256(content.encode()).hexdigest(),
    )


def _prepared() -> PreparedAnswer:
    evidence = SearchEvidence(
        rank=1,
        evidence=_chunk(),
        lexical_rank=1,
        vector_rank=1,
        rrf_score=2 / 61,
    )
    return PreparedAnswer(
        request=AnswerRequest("How is recovery performed?", INDEX_ID, AnswerMode.FIXTURE),
        policy=GROUNDED_ANSWER_V1,
        index=_index(),
        evidence=(evidence,),
    )


class _Embedding:
    identity = EMBEDDING_IDENTITY
    dimension = 384
    model = "reference"
    revision = "runtime-r1"
    checksum = SHA

    def token_count(self, texts: Sequence[str]) -> int:
        return sum(max(1, len(text.split())) for text in texts)

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
        return (EmbeddingVector((1.0,) + (0.0,) * 383, self.identity),)


class _Repository:
    def __init__(self, failures: Sequence[SearchError] = ()) -> None:
        self.failures = list(failures)
        self.resolve_calls = 0

    async def resolve_index(self, index_version: UUID) -> IndexIdentity | None:
        self.resolve_calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return _index() if index_version == INDEX_ID else None

    async def lexical_candidates(
        self, *, index_version: UUID, query: str, depth: int
    ) -> tuple[RankedCandidate, ...]:
        return (RankedCandidate(_chunk(), 1),)

    async def vector_candidates(
        self, *, index_version: UUID, embedding: tuple[float, ...], depth: int
    ) -> tuple[RankedCandidate, ...]:
        return (RankedCandidate(_chunk(), 1),)


class _Generation:
    identity = FIXTURE_IDENTITY

    def __init__(self, *, delay: float = 0, failure: Exception | None = None) -> None:
        self.delay = delay
        self.failure = failure
        self.calls = 0

    async def generate(self, request: GenerationInput) -> GenerationOutput:
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.failure is not None:
            raise self.failure
        evidence_id = json.loads(request.text)["evidence"][0]["evidence_id"]
        answer = "Recovery requires the status ledger."
        return GenerationOutput(
            json.dumps(
                {
                    "status": "answered",
                    "answer": answer,
                    "citations": [
                        {
                            "answer_start": 0,
                            "answer_end": len(answer),
                            "evidence_ids": [evidence_id],
                        }
                    ],
                }
            ),
            self.identity,
        )


async def _connected() -> bool:
    return False


async def _collect(
    generation: _Generation | DeterministicGroundedAnswerFixture,
    **timing: float,
) -> list[AnswerStreamEvent | None]:
    return [
        item
        async for item in stream_prepared_answer(
            prepared=_prepared(),
            generation=generation,
            request_id=REQUEST_ID,
            is_disconnected=_connected,
            **timing,
        )
    ]


def test_stream_orders_events_and_derives_bounded_citations() -> None:
    items = asyncio.run(_collect(_Generation()))
    events = [item for item in items if item is not None]

    assert [event.type for event in events] == [
        AnswerStreamEventType.STARTED,
        AnswerStreamEventType.RETRIEVAL_COMPLETED,
        AnswerStreamEventType.DELTA,
        AnswerStreamEventType.CITATIONS_COMPLETED,
        AnswerStreamEventType.COMPLETED,
    ]
    assert [event.sequence for event in events] == [1, 2, 3, 4, 5]
    citation = events[3].payload["citations"][0]
    assert citation["source_key"] == "status-ledger"
    assert citation["quote"] == "status evidence"

    schema = json.loads(
        (REPOSITORY_ROOT / "contracts" / "events" / "answer-stream.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for event in events:
        frame = encode_answer_event(event).decode()
        data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
        validator.validate(json.loads(data_line[6:]))


def test_stream_is_backpressured_until_consumer_requests_next_event() -> None:
    async def exercise() -> None:
        generation = _Generation()
        stream = stream_prepared_answer(
            prepared=_prepared(),
            generation=generation,
            request_id=REQUEST_ID,
            is_disconnected=_connected,
        )
        started = await anext(stream)
        assert started is not None
        assert started.type is AnswerStreamEventType.STARTED
        assert generation.calls == 0
        retrieval = await anext(stream)
        assert retrieval is not None
        assert retrieval.type is AnswerStreamEventType.RETRIEVAL_COMPLETED
        assert generation.calls == 0
        delta = await anext(stream)
        assert delta is not None
        assert delta.type is AnswerStreamEventType.DELTA
        assert generation.calls == 1
        async for _ in stream:
            pass

    asyncio.run(exercise())


def test_waiting_generation_emits_unsequenced_heartbeat() -> None:
    items = asyncio.run(
        _collect(
            _Generation(delay=0.01),
            heartbeat_interval_seconds=0.001,
            disconnect_poll_seconds=0.001,
        )
    )
    assert None in items
    assert HEARTBEAT_FRAME == b": heartbeat\n\n"


def test_post_header_provider_failure_is_one_content_free_terminal_event() -> None:
    secret = "private-provider-output"
    items = asyncio.run(_collect(_Generation(failure=RuntimeError(secret))))
    events = [item for item in items if item is not None]

    assert [event.type for event in events] == [
        AnswerStreamEventType.STARTED,
        AnswerStreamEventType.RETRIEVAL_COMPLETED,
        AnswerStreamEventType.FAILED,
    ]
    encoded = encode_answer_event(events[-1])
    assert b"provider.unavailable" in encoded
    assert secret.encode() not in encoded


def test_disconnect_cancels_and_awaits_provider_cleanup(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cleaned = asyncio.Event()

    class _CancellableGeneration:
        identity = FIXTURE_IDENTITY

        async def generate(self, request: GenerationInput) -> GenerationOutput:
            try:
                await asyncio.Event().wait()
                raise AssertionError("unreachable")
            finally:
                cleaned.set()

    checks = 0

    async def disconnected() -> bool:
        nonlocal checks
        checks += 1
        return checks > 1

    async def exercise() -> list[object]:
        return [
            item
            async for item in stream_prepared_answer(
                prepared=_prepared(),
                generation=_CancellableGeneration(),
                request_id=REQUEST_ID,
                is_disconnected=disconnected,
                disconnect_poll_seconds=0.001,
            )
        ]

    with caplog.at_level("INFO"):
        items = asyncio.run(exercise())

    assert len(items) == 2
    assert cleaned.is_set()
    record = next(record for record in caplog.records if record.msg == "answer stream cancelled")
    assert record.__dict__["request_id"] == str(REQUEST_ID)
    assert record.__dict__["code"] == "stream.cancelled"
    assert not hasattr(record, "question")


def test_pre_byte_retry_is_once_and_only_for_typed_transient_dependencies() -> None:
    transient = SearchError(SearchErrorCode.DATABASE_UNAVAILABLE, "content-free")
    repository = _Repository((transient,))
    prepared = asyncio.run(
        prepare_stream_answer(
            request=_prepared().request,
            embedding=_Embedding(),
            repository=repository,
            policy=GROUNDED_ANSWER_V1,
        )
    )
    assert prepared.index.index_version_id == INDEX_ID
    assert repository.resolve_calls == 2

    unsafe_repository = _Repository(
        (SearchError(SearchErrorCode.RETRIEVAL_CONFIGURATION_MISMATCH, "content-free"),)
    )
    with pytest.raises(SearchError):
        asyncio.run(
            prepare_stream_answer(
                request=_prepared().request,
                embedding=_Embedding(),
                repository=unsafe_repository,
                policy=GROUNDED_ANSWER_V1,
            )
        )
    assert unsafe_repository.resolve_calls == 1


def test_invalid_timing_bounds_fail_before_streaming() -> None:
    async def exercise() -> None:
        stream: AsyncIterator[object] = stream_prepared_answer(
            prepared=_prepared(),
            generation=_Generation(),
            request_id=REQUEST_ID,
            is_disconnected=_connected,
            heartbeat_interval_seconds=0,
        )
        await anext(stream)

    with pytest.raises(ValueError, match="timing bounds"):
        asyncio.run(exercise())
