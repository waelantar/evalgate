# R3 release-readiness record

- Candidate: first stable R3 release
- Audited product version: `0.12.0`
- Audited merged-main commit: `2fe78860fa4c3787dbd277c79f79dee6d46c6f1e`
- Requested target: `1.0.0`
- Review date: 2026-09-19
- Status: **blocked; do not tag, publish, deploy, or claim a `1.0.0` release**
- Publication state: not pushed by EG-014, not deployed, and not released

This is the final EG-014 audit of the merged EG-017, EG-018, and EG-019 candidate. It reconciles
the R3 checklist in `BLUEPRINT.md` section 18 without treating a passing unit/E2E matrix as proof
that the governed retrieval, security, accessibility, CI, and final-image gates passed. Because
multiple release gates fail, product metadata remains `0.12.0`; no final `1.0.0` image was built.

## Start conditions and repeatable evidence

| Gate | Evidence and result |
| --- | --- |
| Branch precondition | Clean `main` at `2fe7886`; EG-018 commit `c30e712` and EG-019 commit `75b59d0` are ancestors; controlled product metadata is consistently `0.12.0`. |
| Clean checkout | A detached worktree at exact merged `main` completed `scripts/bootstrap.ps1` in 48.3 seconds using Python 3.13.15, uv 0.12.3, Node.js 24.19.0, an isolated Compose project, locked dependencies, PostgreSQL migrations, and Chromium. |
| Static and backend matrix | Publication (268 text files), metadata, release-static, Compose, Ruff format/lint, mypy (70 source files), and 215 non-integration Python tests passed. |
| Frontend matrix | ESLint, 37 Vitest tests, eight Chromium Playwright/axe/responsive/theme flows, and the production Vite build passed. |
| PostgreSQL/reference integration | All 15 integration tests passed against an isolated PostgreSQL 18/pgvector service and the verified local reference-embedding snapshot. |
| Contract/ADR reconciliation | All accepted ADRs were reviewed and every JSON contract parsed successfully. OpenAPI, stream, corpus, prompt, retrieval, evaluation, review, and release schemas remain present. |
| Governed retrieval | **Failed.** Fresh Northstar ingestion created 161 chunks and the expected index UUID, but the 36-case gate produced precision@5 `0.005556`, recall@5 `0.027778`, MRR `0.027778`, nDCG@5 `0.027778`, and source coverage `0.027778`. |
| Exact-main remote CI | **Failed** on the same retrieval gate for the same metrics: [CI run 35444229759](https://github.com/waelantar/evalgate/actions/runs/35444229759). This is linked negative evidence, not a successful release run. |
| Governed live evidence | EG-015 and EG-018 reviewed artifacts, costs, provider failures, and limitations remain linked from `docs/evaluation/README.md`. They are evaluation evidence, not a generation-quality or deployment claim. |
| Dependency audit | `npm audit --omit=dev --json` reports zero production vulnerabilities. Full `npm audit --json` reports one high (`js-yaml`) and three moderate Vitest/tooling findings; these remain unresolved and the full dependency gate fails. |
| Accessibility | Eight Chromium/axe flows pass. Screen-reader behavior, keyboard spot checks, 200% zoom, and forced-colors/high-contrast rows in `docs/accessibility/EG-013B-manual-review.md` remain pending human review. |
| Container scan | **Unavailable.** Neither Trivy nor Grype is installed. A `waived_tool_unavailable` record is not an acceptable first-stable-release scan. |
| Image and SBOM | Only the earlier local `evalgate-api:0.9.0` candidate image/SBOM exists. No `0.12.0` or `1.0.0` release image, matching digest, final scan, or release-attached SBOM was created. |

## Retrieval regression diagnosis

EG-018 generalized the corpus loader and changed chunk ordinal assignment from the original
per-document section ordinal to `len(chunks)`, a corpus-global ordinal. PostgreSQL evidence UUIDs
are UUIDv5 values derived from index UUID, document UUID, chunk ordinal, and content hash. The
Northstar corpus text, index UUID, and ranking policy stayed stable, but almost every evidence UUID
after the first document changed. `contracts/evaluation/golden-v1.json` correctly retained the
reviewed IDs, so the gate exposed the mismatch instead of silently accepting a new baseline.

This is not repaired on the documentation-only EG-014 branch. [EG-020](../backlog/EG-020-northstar-evidence-identity.md)
owns the narrow fix and must preserve both the original Northstar identities and the accepted
Kubernetes showcase identities. Updating the dataset or baseline to match the regression is
explicitly forbidden.

## Release-blocking gaps

1. **EG-020 / retrieval identity:** restore reviewed Northstar evidence IDs without changing
   either governed dataset or accepted Kubernetes artifacts; rerun the real reference baseline.
2. **Successful exact-commit CI:** after EG-020, link a successful secret-free CI run for the exact
   candidate commit and its immutable retrieval artifact.
3. **EG-021 / dependency findings:** resolve the one high and three moderate development
   dependency advisories without unrelated upgrades; the production-only audit being
   clean does not make the complete release gate green.
4. **EG-021 / container vulnerability scan:** run Trivy or Grype against the final candidate, review every
   result, and leave no unresolved high or critical finding. Tool unavailability is not accepted.
5. **Manual accessibility:** a human must complete and date the screen-reader, keyboard, 200% zoom,
   and forced-colors checks. Automated axe evidence cannot be substituted.
6. **Final image evidence:** only after all pre-bump gates pass may EG-014 apply `1.0.0`, rebuild the
   unchanged accepted image definition, and record matching runtime version, digest, smoke,
   graceful stop, scan, SBOM, and consistency evidence.

## Commands and outcomes

```powershell
./scripts/bootstrap.ps1
./scripts/check.ps1
uv run --python 3.13.15 --locked pytest -m integration
uv run --python 3.13.15 --locked evalgate-ingest --corpus northstar-operations
uv run --python 3.13.15 --locked evalgate-evaluate --mode retrieval `
  --index-version 6932f8da-e71b-533f-ae2b-4c969cd3acd2 `
  --output ../../artifacts/retrieval-eg014-final.json
python scripts/check_retrieval_baseline.py `
  --artifact artifacts/retrieval-eg014-final.json `
  --baseline contracts/evaluation/retrieval-baseline-v1.json
npm audit --json
npm audit --omit=dev --json
gh run view 35444229759 --log-failed
```

Bootstrap, static/backend/frontend checks, and integration tests passed. The baseline command and
full npm audit failed as documented above. The local retrieval artifact was generated only inside
the disposable trial and is not a release artifact.

## Security, privacy, operations, and claim boundary

- Threat model, public-mode denial, content-free logging, server-side secret handling, bounded
  controls, and runbooks remain implemented and tested locally; no public ask or deployment is
  enabled by this record.
- Kubernetes source provenance, CC BY 4.0 attribution/transformation disclosure, reviewed cases,
  OpenRouter costs, and failed/weak model results remain explicit. They are not a benchmark or
  endorsement claim.
- Browser upload, accounts, workspace tenancy, hosted private storage, cloud resources, and public
  mutation are not implemented and are not implied by the onboarding UI.
- No provider call, spending, baseline update, push, merge, tag, release, or deployment occurred in
  EG-014.

## Version handoff and recommendation

**No release. Keep `0.12.0`.** Review and merge this audit, complete EG-020 as `0.12.1`,
complete EG-021 as `0.12.2`, finish human accessibility review, and obtain successful exact-commit
CI. Then rerun EG-014 from clean accepted `main`. Only an all-green pre-release matrix may perform
the controlled `0.12.2 -> 1.0.0` bump and final image evidence sequence.
