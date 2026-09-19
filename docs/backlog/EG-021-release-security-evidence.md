# EG-021: Close dependency and container-scan gates

- Status: Planned from the EG-014 release-blocking security findings
- Branch: `chore/eg-021-release-security-evidence`
- Depends on: EG-020 merged to `main`
- Release: R3
- Version action: Patch `0.12.1 -> 0.12.2`
- Codex profile: `gpt-5.6-sol` with `medium` reasoning
- Blueprint requirements: NFR-04/05/09/10/11 and section 18 security/release gates

## Outcome

The complete locked dependency set has no unresolved audit finding accepted by the release policy,
and a reproducible Trivy or Grype scan plus CycloneDX SBOM exists for the pre-stable candidate image.
The image/runtime metadata agrees at `0.12.2`; this remains pre-release evidence, not `1.0.0`.

## Scope

- Reverify current official npm and selected scanner guidance at story start.
- Upgrade only the dependency paths responsible for the EG-014 findings (`vitest`,
  `@vitest/coverage-v8`, `@vitest/mocker`, and transitive `js-yaml`) using compatible locked updates.
- Add or document one pinned, reproducible Trivy-or-Grype invocation that does not rely on an
  unversioned mutable tool and fails on unresolved high/critical container findings.
- Align the pre-stable image label, Compose tag, smoke expectations, release scripts, and their
  direct assertions to the accepted `0.12.2` candidate without changing runtime behavior.
- Regenerate local smoke, graceful-stop, CycloneDX SBOM, scan summary, image ID/digest, and
  publication-state evidence. Artifacts remain ignored/local unless a later release attaches them.

## Non-goals

- Functional product changes, dependency major upgrades unrelated to an observed finding,
  suppressing advisories without review, accepting a high/critical waiver, cloud/deployment work,
  publishing an image/SBOM, or declaring/tagging `1.0.0`.

## Acceptance evidence

- [ ] `npm audit --json` and `npm audit --omit=dev --json` have no unresolved finding under the
      accepted release policy; every changed lockfile path maps to an EG-014 finding.
- [ ] Python locked dependencies are scanned/reviewed with a documented reproducible command.
- [ ] The candidate image runs non-root, reports `0.12.2`, passes live/ready/graceful-stop smoke,
      and is identified by immutable image ID/digest.
- [ ] Trivy or Grype produces machine-readable results with no unresolved high/critical finding.
- [ ] A CycloneDX SBOM is generated for the exact scanned image.
- [ ] Publication/metadata checks, `scripts/check.ps1`, all 15 integration tests, and image evidence
      pass before and after the controlled patch bump as applicable.

## Expected file ownership

- `apps/web/package.json` and `apps/web/package-lock.json`
- Pinned dependency/scan automation and direct tests only
- `Dockerfile`, `compose.yaml`, release scripts/static assertions for version metadata only
- Product-version surfaces in `docs/WORKFLOW.md`, `CHANGELOG.md`, and this story evidence

## Stop conditions

- Remediation requires an unrelated major upgrade, product/runtime redesign, unreviewed waiver,
  unpinned scanner, publishing, or any high/critical finding cannot be closed.
- The built image differs from the accepted runtime definition beyond controlled metadata and the
  narrowly reviewed dependency remediation.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `medium`. Do not substitute the model or raise effort; stop if unavailable. Version action: after every audit/image/scan gate passes, apply only the patch bump `0.12.1 -> 0.12.2` through the controlled product-version surfaces and rerun version-bound evidence. Work only on EG-021 on branch
> `chore/eg-021-release-security-evidence` from clean merged `main` at exactly `0.12.1`. Read
> `AGENTS.md`, BLUEPRINT section 18, EG-013D, EG-014 readiness, EG-020, `docs/WORKFLOW.md`, and this
> story. Reverify current official npm and selected Trivy/Grype guidance. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Reproduce the full and
> production-only audits, update only dependency paths that close the recorded Vitest/js-yaml
> findings, and do not use a blind or forced upgrade. Establish one pinned reproducible container
> scan, align only pre-stable image/version metadata and direct assertions, then build one exact
> candidate and record non-root smoke, readiness, graceful stop, immutable ID/digest, CycloneDX
> SBOM, and machine-readable scan with no unresolved high/critical finding. Run publication,
> metadata, full repository, all integration, audit, image, scan, and SBOM checks. Only after all
> pre-bump gates pass, apply `0.12.1 -> 0.12.2` through controlled surfaces and regenerate affected
> evidence. Do not implement features, refactor unrelated code, waive findings, publish, push,
> merge, deploy, spend, call a provider, tag/release, or start EG-014. Finish with advisory-to-lock
> mapping, scanner identity, image/digest/SBOM mapping, commands/results, limitations, and commit.
