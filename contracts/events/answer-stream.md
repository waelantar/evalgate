# Answer stream wire contract

- Status: Draft
- Owner: EG-007
- Schema version: 1.0-draft

This contract is not implemented by the foundation. EG-007 must freeze examples and machine-readable schemas before transport code.

## Transport

- Request: `POST /api/v1/ask` with bounded JSON.
- Response: `text/event-stream; charset=utf-8` consumed through browser `fetch`.
- Headers: `Cache-Control: no-cache, no-transform` and host-specific buffering control.
- Frame: `event` line, decimal `id` line, one JSON `data` line, then a blank line.
- Every data object: `schema_version`, server `request_id`, strictly increasing `sequence`.
- Heartbeat comments carry no sequence and no application data.

## Ordered events

```text
answer.started
retrieval.completed
answer.delta*
citations.completed
answer.completed | answer.failed | answer.cancelled
```

There is exactly one terminal event and nothing follows it. The UI does not activate citation affordances before `citations.completed`. The model emits evidence IDs only; server code derives trusted source metadata and quotes.

## Required contract tests

UTF-8 split boundaries, partial frames, multiple frames per chunk, malformed JSON, unknown event version, duplicate/out-of-order sequence, terminal enforcement, heartbeat handling, bounded backpressure, disconnect cleanup, cancellation, pre-header Problem Details, and post-header failure.
