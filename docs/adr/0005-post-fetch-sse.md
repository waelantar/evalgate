# ADR-0005: POST plus fetch-consumed SSE framing

- Status: Accepted
- Date: 2026-08-08
- Story: EG-007

## Context

The ask operation needs a bounded JSON request body and incremental typed output. Native EventSource cannot issue POST.

## Decision

`POST /api/v1/ask` returns UTF-8 SSE-framed events consumed with browser `fetch`. Events have explicit type, sequence ID, JSON data, and one terminal outcome. Browser cancellation uses AbortController and propagates to server/provider cleanup.

## Consequences

The client needs a tested frame parser. There is no resume or automatic retry, and answer deltas may not be dropped under backpressure.

## Verification

Ordering, UTF-8, malformed frame, duplicate, terminal, disconnect, cancellation, proxy-buffering, and timeout tests.
