# EG-013C: Redacted observability and cost controls

- Status: Planned; EG-013 epic child
- Branch: `feat/eg-013c-observability-cost`
- Depends on: EG-010 and EG-011 merged to `main`
- Release: R3
- Version action: Patch `0.8.2 -> 0.8.3`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: NFR-07, NFR-08

## Outcome

Operators can diagnose bounded failures and disable expensive generation using low-cardinality metrics, structured content-free logs, layered limits, and a tested kill switch.

## Scope

- Structured event/log schema with request/run IDs, versions, durations, status/error codes, usage/cost fields, and mandatory redaction.
- Metrics for requests, search, streams, providers, evaluation, database pool, allowances, and kill-switch state without high-cardinality labels.
- Provider-neutral input/output token, timeout, per-client/global concurrency, daily allowance, and account-cap configuration/interfaces.
- Simple provider cooldown and kill-switch behavior with operator-visible state.

## Non-goals

- Provider selection/call, vendor dashboard, distributed tracing, Prometheus/Grafana stack, paging/SLO promise, host provisioning, or IP-only cost control.

## Acceptance evidence

- [ ] Success/failure/cancellation/outage tests assert useful structured telemetry and absence of content/secrets/raw IP.
- [ ] Concurrency, token, daily allowance, cooldown, and kill switch reject safely in tests.
- [ ] Metric labels pass a cardinality review; documented measurements use declared conditions.
- [ ] No silent fixture fallback occurs during provider failure/cooldown.

## Required tests and review

- Run success/failure/cancel/outage telemetry, redaction, label-cardinality, token/concurrency/daily-limit, cooldown, kill-switch, and no-fallback tests; review operational usefulness without content leakage.

## Expected file ownership

- Structured logging/metric contracts and adapters, provider-neutral usage/limit/cooldown/kill-switch application policy, focused tests, operator-visible status, and operations documentation.

## Stop conditions

- A monitoring vendor, host edge, provider account API, or new persistence service is required.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.8.2` on the latest accepted `main`, apply only the declared patch to `0.8.3` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-013C on branch `feat/eg-013c-observability-cost`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0006, ADR-0009, and this story. Confirm dependencies are merged to clean `main`. Implement content-free structured telemetry, low-cardinality metrics, provider-neutral layered limits, cooldown, and a tested kill switch. Do not select/call a provider, add an observability stack/vendor, set invented SLOs, use raw IP as the only control, deploy, or silently fall back. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, tag/release, or start another story. Finish with telemetry/limit flow, files, exact tests, cardinality/redaction review, limitations, version handoff, and suggested commit message.
