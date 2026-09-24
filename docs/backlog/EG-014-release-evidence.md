# EG-014: R3 release evidence and documentation reconciliation

- Status: Complete; final `1.0.0` release evidence passed locally, pending merged-main CI before tag
- Branch: `release/eg-014-1.0.0`
- Depends on: EG-013D, EG-015, EG-017, EG-018, EG-019, EG-020, EG-021, and EG-022 merged to `main`
- Release: R3
- Version action: First stable release `0.12.3 -> 1.0.0`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: all R3 Must requirements and section 18

## Outcome

A reviewer can reproduce the product from a clean checkout and verify that blueprint, ADRs, contracts, code, migrations, UI, tests, evaluation evidence, security posture, and status claims agree.

## Scope

- Clean-checkout setup trial on declared environments with timing and exact commands.
- Run and index all required format/lint/type/unit/integration/contract/E2E/accessibility/evaluation/security/image checks.
- Reconcile requirements-to-story-to-test traceability, architecture diagrams, OpenAPI/schemas, migrations, README/status, changelog, runbooks, scans, SBOM, baseline/live artifacts, and limitations.
- Reconcile the EG-017 product-experience, EG-018 real-world showcase/model-comparison, and EG-019 product-shell/onboarding evidence without converting their limitations into release claims.
- Synchronize controlled product metadata to `1.0.0`, rebuild the final image from unchanged accepted definitions, and rerun image-version, smoke, scan, SBOM, and digest evidence.
- Prepare release-readiness record and release notes; leave any future deployment, public image publication, hosted upload, accounts, or storage outside this story.

## Non-goals

- New capability, refactor, baseline update, deployment, public image/package publication, fixing unrelated failures, or checking a box without evidence.

## Acceptance evidence

- [x] Bootstrap, the standard matrix, all 16 integrations, and the required 36-case retrieval gate succeed; exact results are linked in `docs/release/READINESS.md`.
- [x] Every R3 requirement is implemented/verified or explicitly scoped out of the source release; no orphan contract or story exists.
- [x] Retrieval and governed live artifacts plus known-bad rejection are linked with limitations.
- [x] Security/accessibility/scans/SBOM/runbook/rollback evidence is reconciled with truthful status.
- [x] The final image and runtime report `1.0.0`, and the release record identifies its matching digest, scans, and SBOM.

The conditional stable-version criterion is closed by EG-014 evidence. The final publication gate is operational: merge the release PR, require exact merged-main CI to pass, then create the `v1.0.0` source tag and GitHub Release. Do not deploy or publish the Docker image.

## Required tests and review

- Re-run the complete R3 check matrix from a clean checkout and independently reconcile every requirement, story, contract, ADR, artifact, image digest, runbook, limitation, and status claim; this story adds no product test code.

## Expected file ownership

- `README.md`, `BLUEPRINT.md`, traceability/status/changelog, release-readiness and evidence indexes, reconciled architecture/contracts documentation, release notes, the controlled product-version surfaces in `docs/WORKFLOW.md`, and final image evidence only.

## Stop conditions

- Any failing gate, blueprint/code mismatch, unreviewed waiver, missing license/provenance, or feature work is discovered.
- Final image construction would require an image-definition, dependency, runtime, or product fix rather than only the approved version metadata.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: first verify every pre-release gate against `0.12.3`. If and only if all pass, apply `1.0.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add/finalize the changelog and release evidence, rebuild the final image from unchanged accepted definitions, and rerun image-version, smoke, scan, SBOM, digest, and consistency checks. If any pre- or post-bump gate fails, retain/restore `0.12.3`, leave the gap open, and recommend no release. Work only on EG-014 finalization on branch `release/eg-014-1.0.0`. Read `AGENTS.md`, the complete `BLUEPRINT.md`, all accepted ADRs/contracts, release checklist, EG-017/EG-018/EG-019/EG-020/EG-021/EG-022 evidence, and this story. Confirm EG-013D, EG-015, EG-017, EG-018, EG-019, EG-020, EG-021, and EG-022 are merged to clean `main`. Perform a clean-checkout trial, run/index every R3 check and artifact, reconcile all docs/contracts/status/traceability including the product-experience and real-world showcase evidence, and prepare an honest readiness record. Do not implement/fix features or image definitions, auto-update a baseline, create a tag/release, deploy, publish a Docker image/package, or mark failed/missing evidence complete. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Stop and report any blocker. Finish with an evidence map, exact commands/results, open risks/waivers, release recommendation, version handoff, and suggested commit message.