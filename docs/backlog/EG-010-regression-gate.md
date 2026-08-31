# EG-010: Reviewed retrieval baseline and PR regression gate

- Status: Implementation awaiting final pinned-tool verification
- Branch: `feat/eg-010-regression-gate`
- Depends on: EG-009 merged to `main`
- Release: R2
- Version action: Patch `0.6.0 -> 0.6.1`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: G-04, G-05, FR-07, NFR-04

## Outcome

Pull requests receive a repeatable, secret-free retrieval regression decision against an immutable reviewed baseline, and a seeded bad change proves the policy can fail.

## Scope

- Baseline proposal/change-record schema and human review policy.
- Calibrate metric/tolerance thresholds from repeated real retrieval runs.
- CI job using ephemeral PostgreSQL and pinned public embedding artifact/cache.
- Immutable JSON/Markdown upload keyed by Git SHA and clear case-level diff.
- A test-only known-bad retrieval change that must be rejected.

## Non-goals

- Automatic baseline update, live generation/judge, CI writes to deployed state, provider secrets, arbitrary fixed thresholds, or deployment.

## Acceptance evidence

- [x] Repeated retrieval evidence and threshold rationale are recorded in the reviewed baseline.
- [x] Good reference run passes; seeded known-bad artifact fails metric comparison.
- [x] Fork pull-request path remains secret-free with `contents: read`; it uploads only immutable artifacts and cannot update baseline or deploy.
- [x] Baseline is a checked-in reviewed record; CI only compares and never writes it.

## Required tests and review

- Run repeated reference baselines, known-good and seeded known-bad policy cases, artifact-diff tests, and a fork-equivalent secret-free CI exercise; review thresholds, tolerances, action pins, permissions, and baseline-change records.

## Expected file ownership

- Reviewed baseline/policy records, comparison scripts/tests, known-bad fixture, retrieval-gate workflow, immutable artifact configuration, and baseline governance documentation.

## Stop conditions

- Real retrieval is too variable for a stable gate, action/model artifacts cannot be pinned, or the policy would hide case regressions behind an aggregate.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.6.0` on the latest accepted `main`, apply only the declared patch to `0.6.1` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-010 on branch `feat/eg-010-regression-gate`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0006, the EG-009 artifact contract, and this story. Confirm EG-009 is merged to clean `main`. Calibrate and document a reviewed retrieval baseline/policy from repeated evidence, add secret-free CI artifact comparison, and prove sensitivity with a known-bad change. Never auto-update a baseline, call a live provider/judge, expose secrets, deploy, or write to application state. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, tag/release, or start another story. Finish with threshold/tolerance rationale, CI security explanation, changed files, pass/fail evidence, residual flakiness, version handoff, and suggested commit message.
