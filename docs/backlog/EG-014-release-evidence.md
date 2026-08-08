# EG-014: R3 release evidence and documentation reconciliation

- Status: Planned
- Branch: `docs/eg-014-release-evidence`
- Depends on: EG-013D and EG-015 merged to `main`
- Release: R3
- Blueprint requirements: all R3 Must requirements and section 18

## Outcome

A reviewer can reproduce the product from a clean checkout and verify that blueprint, ADRs, contracts, code, migrations, UI, tests, evaluation evidence, security posture, and status claims agree.

## Scope

- Clean-checkout setup trial on declared environments with timing and exact commands.
- Run and index all required format/lint/type/unit/integration/contract/E2E/accessibility/evaluation/security/image checks.
- Reconcile requirements-to-story-to-test traceability, architecture diagrams, OpenAPI/schemas, migrations, README/status, changelog, runbooks, scans, SBOM, baseline/live artifacts, and limitations.
- Prepare release-readiness record and release notes; leave checklist failures open and visible.

## Non-goals

- New capability, refactor, baseline update, deployment, release tag/push, fixing unrelated failures in this documentation branch, or checking a box without evidence.

## Acceptance evidence

- [ ] Fresh-checkout trial succeeds and links exact versions/results.
- [ ] Every R3 requirement is implemented/verified or explicitly blocks release; no orphan contract or story exists.
- [ ] Retrieval and governed live artifacts plus known-bad rejection are linked with limitations.
- [ ] Security/accessibility/scans/SBOM/runbook/rollback evidence is complete and status language is truthful.

## Required tests and review

- Re-run the complete R3 check matrix from a clean checkout and independently reconcile every requirement, story, contract, ADR, artifact, image digest, runbook, limitation, and status claim; this story adds no product test code.

## Expected file ownership

- `README.md`, `BLUEPRINT.md`, traceability/status/changelog, release-readiness and evidence indexes, reconciled architecture/contracts documentation, and release notes only.

## Stop conditions

- Any failing gate, blueprint/code mismatch, unreviewed waiver, missing license/provenance, or feature work is discovered.

## Copy-paste coding-agent brief

> Work only on EG-014 on branch `docs/eg-014-release-evidence`. Read `AGENTS.md`, the complete `BLUEPRINT.md`, all accepted ADRs/contracts, release checklist, and this story. Confirm EG-013D and EG-015 are merged to clean `main`. Perform a clean-checkout trial, run/index every R3 check and artifact, reconcile all docs/contracts/status/traceability, and prepare an honest readiness record. Do not implement/fix features in this branch, auto-update a baseline, merge, tag, push, deploy, or mark failed/missing evidence complete. Stop and report any blocker. Finish with an evidence map, exact commands/results, open risks/waivers, release recommendation, and suggested commit message.
