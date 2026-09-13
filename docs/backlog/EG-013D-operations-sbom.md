# EG-013D: Operational hardening, release image, and SBOM

- Status: Implemented locally; Docker/supply-chain evidence produced by local release scripts before owner review
- Branch: `feat/eg-013d-operations-sbom`
- Depends on: EG-013A, EG-013B, EG-013C, and EG-015 merged to `main`
- Release: R3
- Version action: Minor `0.8.3 -> 0.9.0`
- Codex profile: `gpt-5.5` with `medium` reasoning
- Blueprint requirements: NFR-09, NFR-10, NFR-11

## Outcome

EvalGate produces one hardened `0.9.0` release-candidate image/digest with scans and SBOM, and maintainers can reproduce shutdown, outage, reset/restore, rollback, secret-rotation, and kill-switch procedures.

## Scope

- Minimal reproducible production image(s), non-root runtime, health/shutdown handling, pinned base/image digests.
- CI image build, dependency/container/secret/license scans, CycloneDX or SPDX SBOM, immutable artifacts.
- Complete and drill runbooks introduced by implemented failure modes.
- Expand/contract migration and previous-image rollback policy; reproducible database reset/backup waiver record.

## Non-goals

- Final `1.0.0` release declaration, deployment, cloud/IaC, WAF, Kubernetes, automated destructive downgrade, daily backup claim, SOC 2/SLSA level claim, or unperformed incident claim.

## Acceptance evidence

- [x] The `0.9.0` release-candidate image runs non-root, reports the correct product version, handles termination, passes health/smoke, and is identified by digest.
- [x] SBOM evidence is attached; the vulnerability scan is explicitly recorded as a local-tool waiver when Trivy/Grype are unavailable, and the scanner is not mislabeled as the SBOM generator.
- [x] Every required runbook has a recorded local drill, automated-test basis, or release-review limitation with recovery verification.
- [x] Rollback uses a prior digest or documented reset; no unsafe default command exists.

## Implementation evidence

- Built local image `evalgate-api:0.9.0` from the digest-pinned `python:3.13.15-slim-trixie`
  base. The local image ID was
  `sha256:c6c86cc9c95d89935d1c7740c9e5ad9bb80e61f85ffca1062e6ccb50753c7222`.
- `scripts/release_candidate.ps1` verified container user `10001:10001`, `/health/live`
  returned EvalGate `0.9.0`, `/health/ready` returned database `available` and migration
  `current`, and graceful API stop completed with a ten-second grace period.
- `scripts/release_supply_chain.ps1` generated CycloneDX SBOM evidence through local Docker SBOM.
  Trivy and Grype were not available locally, so the container vulnerability scan artifact records
  an explicit tool-unavailable waiver rather than a passed scan.
- `docs/runbooks/R3-operational-drills.md` documents graceful shutdown, provider outage/cooldown,
  database reset/restore, previous-image rollback, credential rotation, and public kill-switch
  recovery. Procedures backed only by EG-013C/EG-015 automated evidence or pending prior-digest
  release review are labeled as such.
- A persistent CI artifact-upload workflow was not added without explicit repository-owner
  approval for the external artifact-publication path.

## Required tests and review

- Run reproducible image build, non-root/health/termination smoke, dependency/container/secret/license scans, SBOM validation, and each shutdown/outage/reset/restore/rollback/rotation/kill-switch drill; review all findings and waivers.

## Expected file ownership

- Production image definitions, release-candidate image/scan/SBOM workflow and scripts, immutable evidence metadata, completed runbooks/drill records, and release/recovery documentation.

## Stop conditions

- A cloud, registry publication, external scanner service, destructive migration, or non-reproducible state changes the recovery policy.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.5`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after pre-bump implementation checks pass, verify `0.8.3` on the latest accepted `main`, apply only the declared minor bump to `0.9.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, then build and validate the version-bearing release-candidate image and rerun all affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-013D on branch `feat/eg-013d-operations-sbom`. Read `AGENTS.md`, `BLUEPRINT.md`, all EG-013 child evidence, the merged EG-015 live adapter, and this story. Confirm EG-013A/B/C and EG-015 are merged to clean `main`. Create and locally verify a minimal non-root release-candidate image containing the complete R3 runtime, immutable digest/scan/SBOM evidence, graceful shutdown and complete drilled runbooks for implemented risks, with safe rollback/reset policy. Do not declare `1.0.0`, deploy, publish images, choose a cloud, add Kubernetes, run destructive downgrades, or claim unperformed assurance. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, tag/release, or start EG-014. Finish with image/operation architecture, files, exact scan/drill evidence, findings/waivers, recovery limitations, version handoff, and suggested commit message.
