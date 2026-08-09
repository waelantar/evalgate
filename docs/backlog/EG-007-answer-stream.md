# EG-007: Versioned answer stream and cancellation

- Status: Planned
- Branch: `feat/eg-007-answer-stream`
- Depends on: EG-006 merged to `main`
- Release: R2
- Version action: Minor `0.3.1 -> 0.4.0`
- Codex profile: `gpt-5.6-sol` with `high` reasoning
- Blueprint requirements: FR-03, FR-04, FR-12, ADR-0005

## Outcome

`POST /api/v1/ask` emits the frozen UTF-8 SSE-framed contract, preserves answer order under backpressure, and cancels downstream work when the client aborts.

## Scope

- Freeze OpenAPI, event JSON Schemas/examples, Problem Details codes, headers, sequence and terminal rules.
- FastAPI stream adapter around the answer use case.
- Bounded buffering/awaited writes, heartbeat policy, disconnect cleanup, timeout and one safe pre-byte retry rule.
- TypeScript fetch/UTF-8 frame parser as transport infrastructure, not a product screen.
- AbortController propagation and non-content cancellation telemetry.

## Non-goals

- Native EventSource, WebSocket, resume/replay, automatic post-byte retry, token dropping, completed UI, or public host selection.

## Acceptance evidence

- [ ] Contract tests cover split UTF-8, partial/multiple frames, ordering, duplicates, malformed data, heartbeats, terminal enforcement, pre/post-header errors.
- [ ] Browser/client abort reaches provider cleanup and no later work is retained.
- [ ] Backpressure never silently drops/reorders answer deltas.
- [ ] Proxy buffering/idle behavior is documented for local tests; host verification remains EG-016.

## Required tests and review

- Run event-schema/OpenAPI tests, UTF-8 parser fixtures, ordering/backpressure/terminal/error cases, browser-abort-to-provider cancellation integration, and disconnect cleanup tests; review wire compatibility and resource bounds.

## Expected file ownership

- Versioned stream event schemas/examples, ask OpenAPI contract, FastAPI stream adapter, TypeScript fetch/SSE parser, cancellation plumbing, transport tests, and local proxy notes.

## Stop conditions

- Transport changes from POST/fetch/SSE, cancellation cannot reach the provider port, or a queue/WebSocket/resume feature is proposed.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `high`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.3.1` on the latest accepted `main`, apply only the declared minor bump to `0.4.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-007 on branch `feat/eg-007-answer-stream`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0005, the draft stream contract, and this story. Confirm EG-006 is merged to clean `main`. Freeze and implement the POST/fetch/SSE wire contract, parser, strict sequencing/terminal rules, bounded backpressure, typed pre/post-header failures, and AbortController-to-provider cancellation with exhaustive contract tests. Do not build the product UI, use EventSource/WebSocket, add resume, or retry after bytes start. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, tag/release, or start EG-008. Finish with wire/cancellation explanation, changed files, exact evidence, cleanup limitations, version handoff, and suggested commit message.
