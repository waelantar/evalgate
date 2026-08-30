"""Strict UTF-8 SSE framing for frozen answer-stream events."""

from __future__ import annotations

import json

from evalgate.application.answer_stream import STREAM_SCHEMA_VERSION
from evalgate.domain.stream import AnswerStreamEvent

HEARTBEAT_FRAME = b": heartbeat\n\n"


def encode_answer_event(event: AnswerStreamEvent) -> bytes:
    """Encode one event with one compact JSON data line and a terminating blank line."""

    data = {
        "schema_version": STREAM_SCHEMA_VERSION,
        "request_id": str(event.request_id),
        "sequence": event.sequence,
        "type": event.type.value,
        **event.payload,
    }
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return f"event: {event.type.value}\nid: {event.sequence}\ndata: {encoded}\n\n".encode()
