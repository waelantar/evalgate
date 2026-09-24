# R3 release-readiness record

- Candidate: first stable R3 release
- Audited product version: `0.12.2`
- Audited merged-main commit: `9ba14d23ac937614473c79f291863d38ece12829`
- Requested target: `1.0.0`
- Review date: 2026-09-24
- Status: **blocked; do not tag, publish, deploy, or claim a `1.0.0` release**
- Publication state: not pushed by EG-014, not deployed, and not released

The EG-014 rerun closes the earlier retrieval, dependency, container-scan, and exact-main CI gaps.
It does not convert partial accessibility evidence into a conformance claim. Product metadata remains
`0.12.2` because browser inspection found a 320px Showcase reflow defect and the mandatory human
accessibility review is incomplete.

## Release-gate evidence

| Gate | Evidence and result |
| --- | --- |
| Merged-main precondition | Clean starting commit `9ba14d2`; EG-020 and EG-021 are ancestors and product metadata is consistently `0.12.2`. |
| Bootstrap | `scripts/bootstrap.ps1` completed in 25.6 seconds with Python 3.13.15, uv 0.12.3, Node.js 24.19.0, locked dependencies, healthy PostgreSQL, and current migrations. |
| Static/backend matrix | Publication (281 text files), metadata, release-static, Compose, Ruff format/lint, mypy (70 source files), and 215 non-integration tests passed. |
| Frontend matrix | ESLint, 37 Vitest tests, eight Chromium Playwright/axe/responsive/theme flows, and the production Vite build passed. |
| PostgreSQL/reference integration | All 16 integration tests passed with the verified local reference snapshot. |
| Governed retrieval | Northstar ingestion produced the accepted 161 chunks/index identity; the unchanged 36-case baseline passed. Local artifact SHA-256: `ca6de1ad632ce65d9d8061c0ecec503a577540700b3119ef2413e2c810d71c66`. |
| Exact-main remote CI | All five jobs passed for exact commit `9ba14d2`: [CI run 35735809199](https://github.com/waelantar/evalgate/actions/runs/35735809199). |
| Dependency audits | Full npm, production-only npm, and the hashed locked Python set with pip-audit 2.10.1 report zero known findings. |
| Candidate image | Rebuilt unchanged as `evalgate-api:0.12.2`, image ID `sha256:494a1359ef7bfdcd664eaf19061b25c856e39e96dc721871359a143ae2b2ed66`; UID/GID `10001:10001`, live/ready checks, migration status, and graceful stop passed. |
| SBOM and container scan | Pinned Trivy 0.74.0 generated an exact-image CycloneDX SBOM. The actionable scan has zero fixable HIGH/CRITICAL findings. The complete report discloses 44 upstream-unfixed HIGH findings. ADR-0014 records the owner-approved policy and claim boundary. |
| Browser structure | Every primary route has one H1, named interactive controls, direct navigation, and compact-menu behavior. Overview, Inspect, Bring data, Evaluations, and System evidence have no document-level overflow at 320px. |
| Responsive Showcase | **Failed.** At 320-by-720 CSS pixels, the Showcase document is 367px wide because process-list content exceeds the viewport. Comparison tables remain correctly scroll-contained. |
| Manual accessibility | **Incomplete.** Human screen-reader status/cancellation/error review, keyboard spot checks, 200% zoom, and forced-colors/high-contrast review remain pending in `docs/accessibility/EG-013B-manual-review.md`. |

## Security decision and exact local evidence

ADR-0014 reconciles the blueprint with the explicit EG-021 owner decision: release fails on fixable
HIGH/CRITICAL container findings, retains the complete HIGH/CRITICAL report, requires an explicit
decision for upstream-unfixed risk, and never describes the image as vulnerability-free.

- Scanner: `aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969` (Trivy 0.74.0)
- CycloneDX SBOM SHA-256: `d6e0bb47a81986d576938f85f3a65ae2f0d1d3b71ec6d383cd4cf5b70184a26b`
- Actionable scan SHA-256: `26f5b9d7fd9fe1e530417b38e8add10924056e92b09b33a6b3f4d2ffc3769dc4`
- All-findings scan SHA-256: `102cf799bb075ea4ce602c2ccd193640fac5e12f4ffda012fc22d3ad7fbab7bd`
- Result: zero actionable findings; 44 disclosed upstream-unfixed HIGH findings; no clean-image claim

These are local, uncommitted generated artifacts. EG-014 did not push an image, SBOM, scan, tag, or
release. A future final `1.0.0` image must regenerate all version-bearing evidence after every
pre-bump gate passes.

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
  --output ../../artifacts/retrieval-eg014-final.json
python scripts/check_retrieval_baseline.py `
  --artifact artifacts/retrieval-eg014-final.json `
  --baseline contracts/evaluation/retrieval-baseline-v1.json
npm audit --json
npm audit --omit=dev --json
uvx --from pip-audit==2.10.1 pip-audit --require-hashes --disable-pip -r <locked-export>
.\scripts\release_candidate.ps1
.\scripts\release_supply_chain.ps1
gh run view 35735809199
```

All commands above passed after Docker Desktop was restarted. Browser-use/CDP then exposed the
Showcase reflow failure; it is recorded rather than fixed on this documentation-only branch.

## Release recommendation and handoff

**No stable release yet. Keep `0.12.2`.** Make one narrow responsive fix with regression coverage,
then have a human complete and date the accessibility checklist. Rerun EG-014 from accepted `main`.
Only an all-green pre-release matrix may perform the controlled `0.12.2 -> 1.0.0` metadata bump and
final image evidence sequence.
