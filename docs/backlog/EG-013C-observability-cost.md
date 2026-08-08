# EG-013C: Redacted observability and cost controls

- Status: Planned; EG-013 epic child
- Branch: `feat/eg-013c-observability-cost`
- Depends on: EG-010 and EG-011 merged to `main`
- Release: R3
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

> Work only on EG-013C on branch `feat/eg-013c-observability-cost`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0006, ADR-0009, and this story. Confirm dependencies are merged to clean `main`. Implement content-free structured telemetry, low-cardinality metrics, provider-neutral layered limits, cooldown, and a tested kill switch. Do not select/call a provider, add an observability stack/vendor, set invented SLOs, use raw IP as the only control, deploy, or silently fall back. Do not merge or push. Finish with telemetry/limit flow, files, exact tests, cardinality/redaction review, limitations, and suggested commit message.
