"""Ordered, bounded answer-stream orchestration with cancellation cleanup."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import suppress
from typing import Any
from uuid import UUID

from evalgate.application.answer import (
    AnswerError,
    AnswerPolicy,
    AnswerRequest,
    PreparedAnswer,
    complete_prepared_answer,
    prepare_answer,
)
from evalgate.application.ports import GenerationPort
from evalgate.application.search import (
    SearchEmbeddingPort,
    SearchError,
    SearchErrorCode,
    SearchRepositoryPort,
)
from evalgate.domain.answer import AnswerResult
from evalgate.domain.stream import AnswerStreamEvent, AnswerStreamEventType

STREAM_SCHEMA_VERSION = "1.0"
MAX_DELTA_CODE_POINTS = 256
HEARTBEAT_INTERVAL_SECONDS = 15.0
DISCONNECT_POLL_SECONDS = 0.05
PRE_BYTE_RETRY_LIMIT = 1

_SAFE_PRE_BYTE_RETRY_CODES = frozenset(
    {SearchErrorCode.DATABASE_UNAVAILABLE, SearchErrorCode.EMBEDDING_UNAVAILABLE}
)

DisconnectCheck = Callable[[], Awaitable[bool]]

_LOGGER = logging.getLogger(__name__)


async def prepare_stream_answer(
    *,
    request: AnswerRequest,
    embedding: SearchEmbeddingPort,
    repository: SearchRepositoryPort,
    policy: AnswerPolicy,
) -> PreparedAnswer:
    """Prepare before headers, retrying one proven-safe read-only dependency failure."""

    for attempt in range(PRE_BYTE_RETRY_LIMIT + 1):
        try:
            return await prepare_answer(
                request=request,
                embedding=embedding,
                repository=repository,
                policy=policy,
            )
        except SearchError as error:
            if error.code not in _SAFE_PRE_BYTE_RETRY_CODES or attempt >= PRE_BYTE_RETRY_LIMIT:
                raise
    raise AssertionError("bounded pre-byte retry loop exhausted without returning or raising")


def _event(
    *,
    event_type: AnswerStreamEventType,
    request_id: UUID,
    sequence: int,
    payload: dict[str, Any],
) -> AnswerStreamEvent:
    return AnswerStreamEvent(event_type, request_id, sequence, payload)


def _citation_payload(result: AnswerResult) -> list[dict[str, object]]:
    return [
        {
            "answer_start": item.answer_start,
            "answer_end": item.answer_end,
            "claim": item.claim,
            "evidence_id": str(item.evidence_id),
            "document_id": str(item.document_id),
            "source_key": item.source_key,
            "title": item.title,
            "license_id": item.license_id,
            "provenance": item.provenance,
            "section_key": item.section_key,
            "source_start": item.source_start,
            "source_end": item.source_end,
            "span_sha256": item.span_sha256,
            "quote": item.quote,
        }
        for item in result.citations
    ]


async def stream_prepared_answer(
    *,
    prepared: PreparedAnswer,
    generation: GenerationPort,
    request_id: UUID,
    is_disconnected: DisconnectCheck,
    heartbeat_interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
    disconnect_poll_seconds: float = DISCONNECT_POLL_SECONDS,
) -> AsyncIterator[AnswerStreamEvent | None]:
    """Yield events one at a time; ``None`` represents an SSE heartbeat comment."""

    if heartbeat_interval_seconds <= 0 or disconnect_poll_seconds <= 0:
        raise ValueError("stream timing bounds must be positive")

    loop = asyncio.get_running_loop()
    started_at = loop.time()

    def record_cancellation() -> None:
        _LOGGER.info(
            "answer stream cancelled",
            extra={
                "event": "answer_stream.cancelled",
                "request_id": str(request_id),
                "status": "cancelled",
                "code": "stream.cancelled",
                "cleanup_duration_ms": round((loop.time() - started_at) * 1000, 3),
            },
        )

    sequence = 1
    yield _event(
        event_type=AnswerStreamEventType.STARTED,
        request_id=request_id,
        sequence=sequence,
        payload={
            "mode": prepared.request.mode.value,
            "prompt_policy": {
                "id": prepared.policy.policy_id,
                "version": prepared.policy.version,
                "sha256": prepared.policy.content_sha256,
            },
        },
    )
    sequence += 1
    yield _event(
        event_type=AnswerStreamEventType.RETRIEVAL_COMPLETED,
        request_id=request_id,
        sequence=sequence,
        payload={
            "index_version": str(prepared.index.index_version_id),
            "corpus_version": str(prepared.index.corpus_version_id),
            "evidence_count": len(prepared.evidence),
            "evidence_ids": [str(item.evidence.evidence_id) for item in prepared.evidence],
        },
    )
    sequence += 1

    if await is_disconnected():
        record_cancellation()
        return

    answer_task = asyncio.create_task(
        complete_prepared_answer(prepared=prepared, generation=generation)
    )
    next_heartbeat = loop.time() + heartbeat_interval_seconds
    try:
        while not answer_task.done():
            timeout = min(disconnect_poll_seconds, max(0.0, next_heartbeat - loop.time()))
            done, _ = await asyncio.wait({answer_task}, timeout=timeout)
            if done:
                break
            if await is_disconnected():
                answer_task.cancel()
                with suppress(asyncio.CancelledError):
                    await answer_task
                record_cancellation()
                return
            if loop.time() >= next_heartbeat:
                yield None
                next_heartbeat = loop.time() + heartbeat_interval_seconds

        try:
            result = await answer_task
        except AnswerError as error:
            yield _event(
                event_type=AnswerStreamEventType.FAILED,
                request_id=request_id,
                sequence=sequence,
                payload={"code": error.code.value},
            )
            return

        assert result.answer is not None
        for start in range(0, len(result.answer), MAX_DELTA_CODE_POINTS):
            yield _event(
                event_type=AnswerStreamEventType.DELTA,
                request_id=request_id,
                sequence=sequence,
                payload={"text": result.answer[start : start + MAX_DELTA_CODE_POINTS]},
            )
            sequence += 1
        yield _event(
            event_type=AnswerStreamEventType.CITATIONS_COMPLETED,
            request_id=request_id,
            sequence=sequence,
            payload={"citations": _citation_payload(result)},
        )
        sequence += 1
        assert result.generation_identity is not None
        yield _event(
            event_type=AnswerStreamEventType.COMPLETED,
            request_id=request_id,
            sequence=sequence,
            payload={
                "status": result.status.value,
                "provider": {
                    "mode": result.generation_identity.mode.value,
                    "name": result.generation_identity.name,
                    "revision": result.generation_identity.revision,
                },
            },
        )
    except asyncio.CancelledError:
        record_cancellation()
        raise
    finally:
        if not answer_task.done():
            answer_task.cancel()
            with suppress(asyncio.CancelledError):
                await answer_task
