# R3 release-readiness record

- Release: EvalGate `1.0.0`
- Release story: EG-014
- Audited predecessor: accepted `main` commit `7d08923c0927937973828a452457447eb9f1b799`
- Release branch: `release/eg-014-1.0.0`
- Review date: 2026-09-24
- Status: **ready for source release after green merged-main CI**
- Publication boundary: source tag and GitHub Release only; no hosted deployment, public image push, package publication, or live-generation quality claim

EG-014 closes the R3 release gates by applying the controlled `0.12.3 -> 1.0.0` product-version bump, rebuilding the final local image from the accepted definitions, and regenerating final smoke, retrieval, SBOM, and scan evidence. The release still preserves the project boundary: EvalGate is a reproducible local product and evidence repository, not a hosted service.

## Release-gate evidence

| Gate | Evidence and result |
| --- | --- |
| Accepted-base precondition | EG-001 through EG-022 are accepted on `main`; predecessor exact-main CI passed for commit `7d08923c0927937973828a452457447eb9f1b799`: [CI run 35986402874](https://github.com/waelantar/evalgate/actions/runs/35986402874). |
| Bootstrap/static matrix | `scripts/bootstrap.ps1` completed with Python 3.13.15, uv 0.12.3, Node.js 24.19.0, locked dependencies, healthy PostgreSQL, current migrations, publication checks for 283 text files, metadata checks, and release-static checks. |
| Backend matrix | Ruff format/lint, mypy across 70 source files, and 215 non-integration API tests passed at `1.0.0`. |
| Frontend matrix | ESLint, 37 Vitest tests, eight Chromium Playwright/axe/responsive/theme flows, and production Vite build passed at `1.0.0`. |
| PostgreSQL/reference integration | All 16 integration tests passed with the verified local reference embedding snapshot. |
| Governed retrieval | Northstar ingestion retained 161 chunks and the accepted index identity; the unchanged 36-case baseline passed. Final artifact SHA-256: `8c6286f805a80c7a848e8b842ef6dd9faa42bf2cb915da7e9a5a64c0d536e008`. |
| Dependency audits | Full npm audit, production npm audit, and the hashed locked Python dependency set with pip-audit 2.10.1 report zero known findings. |
| Final image | Built as `evalgate-api:1.0.0`, image ID `sha256:9a3cfb8f7af95997bb14aae69eb88a88577c5b73cad5ceeaa2824a2b9df51225`; UID/GID `10001:10001`, live/ready checks, migration status, and graceful stop passed. |
| SBOM and container scan | Pinned Trivy 0.74.0 generated an exact-image CycloneDX SBOM. The actionable scan has zero fixable HIGH/CRITICAL findings. The complete report discloses 44 upstream-unfixed HIGH/CRITICAL findings. ADR-0014 records the owner-approved policy and claim boundary. |
| Accessibility | Owner-reported manual review passed on 2026-09-24 using Chrome, Windows Narrator, 200% zoom, and Windows High Contrast; documented in `docs/accessibility/EG-013B-manual-review.md`. This is not a formal WCAG conformance claim. |

## Security decision and exact local evidence

ADR-0014 reconciles the blueprint with the explicit EG-021 owner decision: release fails on fixable HIGH/CRITICAL container findings, retains the complete HIGH/CRITICAL report, requires explicit disclosure for upstream-unfixed risk, and never describes the image as vulnerability-free.

- Scanner: `aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969` (Trivy 0.74.0)
- CycloneDX SBOM SHA-256: `07b6fc8c5e205f219d144d15de7cc76c319439e81247872b7b5ac564ccc6d0af`
- Actionable scan SHA-256: `dfbfa825c305a8be622dca6e8367e431a2ef10830858efbb5318fae8263f1efb`
- All-findings scan SHA-256: `e4479c9a217e554dc1baa374f7a20d2808e44fddcac83f01e2382bac87b93e5f`
- Result: zero actionable findings; 44 disclosed upstream-unfixed HIGH/CRITICAL findings; no clean-image claim

These are local, ignored generated artifacts except where committed evidence explicitly references their hashes. EG-014 does not push the Docker image, deploy a service, or publish a package.

## Governed-evidence and claim boundary

- The reviewed Northstar retrieval gate is current and passes without a baseline change.
- EG-015 and EG-018 live-provider artifacts remain historical, limitation-heavy evidence. They do not prove current generation quality or authorize public live generation.
- Fixture answers demonstrate local contract mechanics only.
- Browser upload, accounts, workspace tenancy, hosted private storage, cloud resources, and public mutation are not implemented or implied.
- No public deployment or hosted URL exists.

## Commands executed

```powershell
.\scripts\bootstrap.ps1
.\scripts\check.ps1
uv run --directory apps/api --python 3.13.15 --locked pytest -m integration
uv run --directory apps/api --python 3.13.15 --locked evalgate-db seed-empty
uv run --directory apps/api --python 3.13.15 --locked evalgate-ingest --corpus northstar-operations
uv run --directory apps/api --python 3.13.15 --locked evalgate-evaluate --mode retrieval `
  --index-version 6932f8da-e71b-533f-ae2b-4c969cd3acd2 `
  --output ../../artifacts/retrieval-eg014-final.json `
  --markdown ../../artifacts/retrieval-eg014-final.md
python scripts/check_retrieval_baseline.py `
  --artifact artifacts/retrieval-eg014-final.json `
  --baseline contracts/evaluation/retrieval-baseline-v1.json
npm audit --json
npm audit --omit=dev --json
uvx --from pip-audit==2.10.1 pip-audit --require-hashes --disable-pip -r <locked-export>
.\scripts\release_candidate.ps1
.\scripts\release_supply_chain.ps1
```

All executable local commands above passed. Before creating `v1.0.0`, require the GitHub CI run for the merged release commit to pass; the GitHub Release body records that final remote evidence.

## Release recommendation

Proceed with the controlled `v1.0.0` source tag and GitHub Release after the release PR merges and exact merged-main CI is green. Do not deploy, publish a Docker image, claim a hosted service, or claim generation-quality success.