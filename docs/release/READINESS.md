# R3 release-readiness record

- Candidate: first stable R3 release
- Audited product version: `0.12.3`
- Audited branch/base: `fix/eg-022-showcase-reflow` from `e3374c4ec95a6ac1b53fb1df5dcca4225e196481`
- Requested target: `1.0.0`
- Review date: 2026-09-24
- Status: **blocked; do not tag, publish, deploy, or claim a `1.0.0` release**
- Publication state: EG-022 is local only; not pushed, deployed, tagged, or released

EG-022 closes the observed 320px Showcase reflow defect and re-verifies the repository, governed
retrieval, dependencies, and exact candidate image at `0.12.3`. It does not convert automated
accessibility evidence into a human conformance review. The mandatory human accessibility checklist
and exact-commit remote CI after owner push/merge remain open before final EG-014.

## Release-gate evidence

| Gate | Evidence and result |
| --- | --- |
| Accepted-base precondition | Clean starting commit `e3374c4`; the EG-014 audit rerun is merged and product metadata is consistently `0.12.3` on the local EG-022 branch. |
| Bootstrap | `scripts/bootstrap.ps1` completed in 25.6 seconds with Python 3.13.15, uv 0.12.3, Node.js 24.19.0, locked dependencies, healthy PostgreSQL, and current migrations. |
| Static/backend matrix | Publication (283 text files), metadata, release-static, Compose, Ruff format/lint, mypy (70 source files), and 215 non-integration tests passed. |
| Frontend matrix | ESLint, 37 Vitest tests, eight Chromium Playwright/axe/responsive/theme flows, including all six primary routes at 320px, and the production Vite build passed. |
| PostgreSQL/reference integration | All 16 integration tests passed with the verified local reference snapshot. |
| Governed retrieval | Northstar ingestion retained the accepted 161 chunks/index identity; the unchanged 36-case baseline passed. Local EG-022 artifact SHA-256: `18fea29c6411f41f36f48c9da7a8e1d9da1f1583925edbc4891308b1d9ecb70a`. |
| Remote CI | Historical exact-main CI is green for predecessor commit `9ba14d2`: [CI run 35735809199](https://github.com/waelantar/evalgate/actions/runs/35735809199). Exact EG-022 commit CI is pending owner push/merge and cannot be claimed locally. |
| Dependency audits | Full npm, production-only npm, and the hashed locked Python set with pip-audit 2.10.1 report zero known findings. |
| Candidate image | Built as `evalgate-api:0.12.3`, image ID `sha256:8783c7ced09bc48d42bde9e79f963c2efc925c7460c422ac8897eed14ebc5bd1`; UID/GID `10001:10001`, live/ready checks, migration status, and graceful stop passed. |
| SBOM and container scan | Pinned Trivy 0.74.0 generated an exact-image CycloneDX SBOM. The actionable scan has zero fixable HIGH/CRITICAL findings. The complete report discloses 44 upstream-unfixed HIGH findings. ADR-0014 records the owner-approved policy and claim boundary. |
| Responsive routes | **Passed.** Every primary route satisfies `scrollWidth <= innerWidth` at 320-by-720 CSS pixels. Long Showcase revision/path content wraps while comparison tables remain locally scroll-contained. |
| Manual accessibility | **Incomplete.** Human screen-reader status/cancellation/error review, keyboard spot checks, 200% zoom, and forced-colors/high-contrast review remain pending in `docs/accessibility/EG-013B-manual-review.md`. |

## Security decision and exact local evidence

ADR-0014 reconciles the blueprint with the explicit EG-021 owner decision: release fails on fixable
HIGH/CRITICAL container findings, retains the complete HIGH/CRITICAL report, requires an explicit
decision for upstream-unfixed risk, and never describes the image as vulnerability-free.

- Scanner: `aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969` (Trivy 0.74.0)
- CycloneDX SBOM SHA-256: `ecae2e28f8bb387a7880506c3989f3c01c72a4d653d8976a271a2ad3476b2fd7`
- Actionable scan SHA-256: `b15e373f387dfbb302ed6279e8f16c77f16caa98e5768720faedf983b9a9928a`
- All-findings scan SHA-256: `87e391397457f5d409490f825ca174b30cde3ea816f3cac42c1b35a5cb997163`
- Result: zero actionable findings; 44 disclosed upstream-unfixed HIGH findings; no clean-image claim

These are local, ignored generated artifacts. EG-022 did not push an image, SBOM, scan, tag, or
release. Final EG-014 must regenerate all version-bearing evidence at `1.0.0` after every remaining
gate passes.

## Governed-evidence and claim boundary

- The reviewed Northstar retrieval gate is current and passes without a baseline change.
- EG-015 and EG-018 live-provider artifacts remain historical, limitation-heavy evidence. The
  Kubernetes artifacts bound to dataset `1.0.0` do not prove current `1.0.1` model quality.
- Fixture answers demonstrate local contract mechanics only.
- Browser upload, accounts, workspace tenancy, hosted private storage, cloud resources, and public
  mutation are not implemented or implied.
- No public deployment or hosted URL exists.

## Commands executed

```powershell
.\scripts\bootstrap.ps1
.\scripts\check.ps1
uv run --directory apps/api --python 3.13.15 --locked pytest -m integration
uv run --directory apps/api --python 3.13.15 --locked evalgate-ingest --corpus northstar-operations
uv run --directory apps/api --python 3.13.15 --locked evalgate-evaluate --mode retrieval `
  --index-version 6932f8da-e71b-533f-ae2b-4c969cd3acd2 `
  --output ../../artifacts/retrieval-eg022.json
python scripts/check_retrieval_baseline.py `
  --artifact artifacts/retrieval-eg022.json `
  --baseline contracts/evaluation/retrieval-baseline-v1.json
npm audit --json
npm audit --omit=dev --json
uvx --from pip-audit==2.10.1 pip-audit --require-hashes --disable-pip -r <locked-export>
.\scripts\release_candidate.ps1
.\scripts\release_supply_chain.ps1
# after owner push: gh pr checks <EG-022-PR>
```

All executable local commands above passed. The regression is also encoded in Playwright and passed
across every primary route; the exact pushed commit still needs remote CI after owner publication.

## Release recommendation and handoff

**No stable release yet. Keep `0.12.3`.** Owner-review and merge EG-022, require its remote CI,
then have a human complete and date the accessibility checklist. Rerun EG-014 from accepted `main`.
Only that all-green pre-release matrix may perform the controlled `0.12.3 -> 1.0.0` metadata bump
and final image evidence sequence.
