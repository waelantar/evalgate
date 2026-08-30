# Answer stream wire contract

- Status: Accepted and frozen
- Owner: EG-007
- Schema version: 1.0
- Machine schema: [`answer-stream.schema.json`](answer-stream.schema.json)
- Canonical examples: [`examples/answer-stream.json`](examples/answer-stream.json)

## Transport and buffering

- Request: `POST /api/v1/ask` with bounded JSON and explicit `mode: fixture`.
- Success response: `text/event-stream; charset=utf-8`, consumed through browser `fetch`.
- Headers: `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`, and
  `Connection: keep-alive` where the ASGI server permits it.
- Frame: one `event` line, decimal `id` line, one compact JSON `data` line, then a blank line.
- The event line equals `data.type`; the ID equals `data.sequence`.
- Every data object carries schema version `1.0`, one server `request_id`, and a strictly
  increasing sequence beginning at 1.
- Heartbeats are exactly `: heartbeat` comments followed by a blank line. They carry no sequence
  or application data and do not reset ordering.
- The server uses an awaited async iterator with no event queue. A slow write therefore stops the
  next event from being produced; deltas are never dropped or reordered.

## Ordered events

```text
answer.started
retrieval.completed
answer.delta+
citations.completed
answer.completed | answer.failed | answer.cancelled
```

`answer.failed` may replace the delta/citation/completion suffix after headers have started. There
is exactly one terminal event and no bytes follow it. Citation affordances remain inactive until
`citations.completed`. Provider output contains evidence IDs only; citation metadata and bounded
quotes in the event are server-derived.

## Errors, retry, and cancellation

Request/dependency/retrieval failures detected before response headers use RFC 9457 Problem
Details. The server may retry one time before headers only for a failed read-only retrieval whose
typed code proves a transient database or embedding dependency failure. Validation, configuration,
provider, and all post-header failures are never retried. No retry is allowed after the first SSE
byte.

Browser cancellation uses `AbortController`. ASGI cancellation or disconnect cancels and awaits
the downstream generation task. A disconnected client normally cannot receive
`answer.cancelled`; cleanup is authoritative. Cancellation telemetry contains request ID, status,
duration, and error code only—never question, prompt, evidence, answer, or quote content.

## Local proxy boundary

The no-transform and buffering headers are locally contract-tested. Heartbeats bound idle periods
in the application stream, but an actual reverse proxy may buffer or enforce a shorter idle
timeout. Host-specific end-to-end verification and configuration remain an EG-016 deployment gate.

## Contract tests

The schema, OpenAPI, UTF-8 split boundaries, partial/multiple frames, malformed JSON, unknown
version/event, duplicate/out-of-order sequence, terminal enforcement, heartbeat handling, bounded
backpressure, pre/post-header errors, safe retry, disconnect cleanup, and cancellation propagation
are required acceptance evidence.
