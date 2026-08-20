# EG-015: Governed live-generation evaluation

- Status: Planned; requires explicit provider, retention, and budget approval before any external call
- Branch: `feat/eg-015-governed-live-eval`
- Depends on: EG-006 and EG-009 merged to `main`, plus external-service decision gate
- Release: R3
- Version action: Minor `0.7.0 -> 0.8.0`
- Codex profile: `gpt-5.5` with `high` reasoning
- Blueprint requirements: G-05, ADR-0006, ADR-0010

## Outcome

One approved generation path produces a versioned, budget-bounded live evaluation artifact with repeated results, human labels, judge-calibration evidence, cost, variance, and honest limitations.

## Scope

- Use current primary sources to decide one generation provider/model strategy, retention/region posture, model version recording, and hard budget; record ADR/approval.
- Server-side adapter implementing the existing generation port with typed errors, usage/cost capture, timeout/cooldown, and no fallback.
- Protected manual/scheduled workflow unavailable to forks; never part of ordinary PR CI.
- Human rubric, calibration expansion as needed, repeated runs, agreement/variance report, advisory judge until adequate.

## Non-goals

- Multiple providers, public endpoint/deployment, model leaderboard, automatic judge gate without calibration, hidden deterministic claim, prompt/content logging, or provider key in browser/CI forks.

## Acceptance evidence

- [ ] Explicit owner approval names provider/model posture, retention, region, budget, and kill criteria before calls.
- [ ] Protected workflow enforces caps and records provider/model/prompt/version/usage/cost/repetitions.
- [ ] Human-vs-judge agreement and case evidence justify advisory/blocking status; inadequate calibration stays advisory.
- [ ] Artifact validates, is reviewed, and cannot be confused with fixture or retrieval-only evidence.

## Required tests and review

- Before approved external calls, run adapter contract/error/cap/redaction and protected-workflow security tests; afterward run bounded repetitions, human-label and judge-calibration analysis, artifact validation, variance/cost review, and kill-criteria verification.

## Expected file ownership

- One approved server-side live adapter, trusted manual/scheduled workflow, live-evaluation configuration and tests, decision ADR/approval record, reviewed artifacts, and calibration/limitations documentation.

## Stop conditions

- No explicit approval/key/budget, retention or model-version behavior is unacceptable/unknown, calibration is inadequate, or spend approaches cap.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.5`, reasoning effort `high`. Do not substitute the model or raise effort; if unavailable, stop before editing. This Codex profile is not approval for an EvalGate provider/model or any external call. Version action: only after explicit external-call approval and all pre-bump adapter, cap, redaction, and workflow-security checks pass, verify `0.7.0` on the latest accepted `main` and apply the declared minor bump to `0.8.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`. Then run the approved bounded live suite against that target version, add the `Unreleased` changelog entry, and validate the final version-bound artifact; if the predecessor or any live gate differs, restore/retain `0.7.0` and stop. Work only on EG-015 on branch `feat/eg-015-governed-live-eval`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0006, ADR-0010, EG-006/EG-009 contracts, and this story. Before any external call, stop and obtain explicit approval for one provider/model, retention/region, secret handling, and hard budget using current primary documentation. Then implement only that adapter and protected bounded evaluation workflow, run the approved repeated suite, calibrate against human labels, and publish a schema-valid reviewed artifact with cost/variance/limitations. Never expose a secret to browser/forks, add providers, silently fall back, deploy, auto-block on an uncalibrated judge, merge, push, or tag/release. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Finish with decision evidence, adapter/eval flow, files, exact results/cost, agreement/limitations, version handoff, and suggested commit message.
