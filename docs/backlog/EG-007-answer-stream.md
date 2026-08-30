# EG-007: Versioned answer stream and cancellation

- Status: Implemented and locally verified; awaiting repository-owner review and manual merge
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

- [x] Contract tests cover split UTF-8, partial/multiple frames, ordering, duplicates, malformed data, heartbeats, terminal enforcement, pre/post-header errors.
- [x] Browser/client abort reaches provider cleanup and no later work is retained.
- [x] Backpressure never silently drops/reorders answer deltas.
- [x] Proxy buffering/idle behavior is documented for local tests; host verification remains EG-016.

## Verification evidence

Local pre-bump verification on 2026-08-30 used Windows, Python 3.13.15, uv 0.12.3,
Node.js 24.19.0, FastAPI 0.141.1, Starlette 1.5.0, and Vitest 4.1.10.

- The complete repository gate passed publication and metadata validation, Ruff formatting and
  lint, strict mypy across 51 source files, 143 non-integration API tests, 21 web tests, frontend
  lint, and the production web build.
- The complete post-bump gate passed with synchronized product version `0.4.0`, 144
  non-integration API tests, 21 web tests, and publication validation over 189 text files.
- The focused Python stream/answer/OpenAPI/contract suite passed 57 tests. A real ASGI request
  cancellation test proves HTTP task cancellation reaches and awaits generation cleanup.
- The dedicated browser transport suite passed 19 tests with 100% branch coverage (55/55) and
  100% function/line coverage for the strict UTF-8 stream parser.
- The server uses no event queue: each frame is yielded only when the ASGI sender requests it.
  Read-only retrieval may retry once only for typed transient dependency errors before headers;
  provider and post-byte work never retries.
- No live provider was called. Local tests verify buffering headers and heartbeats, but real proxy
  buffering and idle-timeout behavior remains an EG-016 host gate. Nothing is released or deployed.

## Required tests and review

- Run event-schema/OpenAPI tests, UTF-8 parser fixtures, ordering/backpressure/terminal/error cases, browser-abort-to-provider cancellation integration, and disconnect cleanup tests; review wire compatibility and resource bounds.

## Expected file ownership

- Versioned stream event schemas/examples, ask OpenAPI contract, FastAPI stream adapter, TypeScript fetch/SSE parser, cancellation plumbing, transport tests, and local proxy notes.

## Stop conditions

- Transport changes from POST/fetch/SSE, cancellation cannot reach the provider port, or a queue/WebSocket/resume feature is proposed.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `high`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.3.1` on the latest accepted `main`, apply only the declared minor bump to `0.4.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-007 on branch `feat/eg-007-answer-stream`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0005, the draft stream contract, and this story. Confirm EG-006 is merged to clean `main`. Freeze and implement the POST/fetch/SSE wire contract, parser, strict sequencing/terminal rules, bounded backpressure, typed pre/post-header failures, and AbortController-to-provider cancellation with exhaustive contract tests. Do not build the product UI, use EventSource/WebSocket, add resume, or retry after bytes start. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, tag/release, or start EG-008. Finish with wire/cancellation explanation, changed files, exact evidence, cleanup limitations, version handoff, and suggested commit message.
