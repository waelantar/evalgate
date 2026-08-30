"""Transport-neutral values for the frozen answer-stream sequence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID


class AnswerStreamEventType(StrEnum):
    """Frozen event names for answer stream schema version 1.0."""

    STARTED = "answer.started"
    RETRIEVAL_COMPLETED = "retrieval.completed"
    DELTA = "answer.delta"
    CITATIONS_COMPLETED = "citations.completed"
    COMPLETED = "answer.completed"
    FAILED = "answer.failed"
    CANCELLED = "answer.cancelled"


@dataclass(frozen=True, slots=True)
class AnswerStreamEvent:
    """One ordered application event before UTF-8 SSE framing."""

    type: AnswerStreamEventType
    request_id: UUID
    sequence: int
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("stream sequence must be positive")


TERMINAL_EVENT_TYPES = frozenset(
    {
        AnswerStreamEventType.COMPLETED,
        AnswerStreamEventType.FAILED,
        AnswerStreamEventType.CANCELLED,
    }
)
