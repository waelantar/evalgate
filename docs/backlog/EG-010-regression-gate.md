# EG-010: Reviewed retrieval baseline and PR regression gate

- Status: Planned
- Branch: `feat/eg-010-regression-gate`
- Depends on: EG-009 merged to `main`
- Release: R2
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

- [ ] Repeated baseline measurements and rationale are attached to the proposal.
- [ ] Good reference run passes; seeded known-bad change fails for the intended case/metric.
- [ ] Fork pull-request path is secret-free, has least permissions, and cannot publish/deploy/update baseline.
- [ ] Baseline changes require a separate reviewed diff and never happen on ordinary CI.

## Required tests and review

- Run repeated reference baselines, known-good and seeded known-bad policy cases, artifact-diff tests, and a fork-equivalent secret-free CI exercise; review thresholds, tolerances, action pins, permissions, and baseline-change records.

## Expected file ownership

- Reviewed baseline/policy records, comparison scripts/tests, known-bad fixture, retrieval-gate workflow, immutable artifact configuration, and baseline governance documentation.

## Stop conditions

- Real retrieval is too variable for a stable gate, action/model artifacts cannot be pinned, or the policy would hide case regressions behind an aggregate.

## Copy-paste coding-agent brief

> Work only on EG-010 on branch `feat/eg-010-regression-gate`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0006, the EG-009 artifact contract, and this story. Confirm EG-009 is merged to clean `main`. Calibrate and document a reviewed retrieval baseline/policy from repeated evidence, add secret-free CI artifact comparison, and prove sensitivity with a known-bad change. Never auto-update a baseline, call a live provider/judge, expose secrets, deploy, or write to application state. Do not merge or push. Finish with threshold/tolerance rationale, CI security explanation, changed files, pass/fail evidence, residual flakiness, and suggested commit message.
