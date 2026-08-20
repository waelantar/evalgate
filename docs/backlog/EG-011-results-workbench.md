# EG-011: Read-only evaluation results workbench

- Status: Planned
- Branch: `feat/eg-011-results-workbench`
- Depends on: EG-008 and EG-009 merged to `main`
- Release: R3
- Version action: Minor `0.6.1 -> 0.7.0`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: FR-08, FR-09, NFR-12

## Outcome

A reviewed CLI-produced artifact can be validated and imported locally, and users can inspect run versions, metrics, limitations, and case failures through a read-only API and accessible UI.

## Scope

- Local/admin CLI import that validates schema, checksum, review record, referenced corpus/index/dataset, size, and idempotency.
- Bounded result/case persistence separated from large immutable raw artifacts.
- Cursor-paginated read-only run list/detail API and typed frontend views.
- Metric deltas, limitations, failed-case evidence, version identity, empty/error states.

## Non-goals

- Interactive run trigger, FastAPI background tasks, queue/worker, CI-to-database write, baseline approval UI, live dashboards, or WebSocket/polling execution state.

## Acceptance evidence

- [ ] Valid reviewed artifact imports idempotently; invalid/unreviewed/oversized/tampered artifacts fail transactionally.
- [ ] CI workflow cannot invoke import and public mode exposes read-only result routes only.
- [ ] API pagination/contracts and UI states have integration, component, accessibility, and E2E coverage.
- [ ] Displayed versions/limitations match the immutable artifact and large raw content is not duplicated unboundedly.

## Required tests and review

- Run schema/checksum/trust/idempotency/rollback import tests, real PostgreSQL persistence and pagination tests, OpenAPI consumer tests, UI component/accessibility/E2E states, and public-route denial tests; review storage bounds.

## Expected file ownership

- Evaluation-result migrations/mappings/repository, local import CLI, read-only OpenAPI/HTTP routes, typed result client/views, import/API/UI tests, and result-storage documentation.

## Stop conditions

- Product needs interactive execution, a durable worker/queue, object storage, or a new artifact identity/persistence policy.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.6.1` on the latest accepted `main`, apply only the declared minor bump to `0.7.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-011 on branch `feat/eg-011-results-workbench`. Read `AGENTS.md`, `BLUEPRINT.md`, the evaluation artifact schema, EG-009 output, and this story. Confirm EG-008 and EG-009 are merged to clean `main`. Implement a local reviewed-artifact import with transactional validation/idempotency, read-only paginated results API, and accessible run/case UI. Do not add evaluation triggering, background tasks, queues, CI database writes, baseline approval, WebSockets, or live polling. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, tag/release, or start hardening. Finish with import/trust-boundary and UI explanation, files, exact tests, storage limits, recovery, version handoff, and suggested commit message.
