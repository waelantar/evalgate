# R3 release-readiness record

- Candidate: first stable R3 release
- Candidate product version: `0.11.0` (EG-018 real-world-showcase candidate)
- Requested target: `1.0.0`
- Review date: 2026-09-19
- Status: **blocked; do not tag, publish, deploy, or claim a `1.0.0` release**
- Publication state: not pushed, not deployed, and not released

This is the EG-014 evidence index. It reconciles the R3 checklist in `BLUEPRINT.md` section 18
without turning planned or waived work into completed assurance. The controlled product-version
surfaces now record the `0.11.0` EG-018 candidate; no final `1.0.0` image was built because the release gates below are
not all satisfied.

## Repeatable local evidence

| Gate | Evidence and result |
| --- | --- |
| Clean checkout | A detached `main` worktree at `d5a4d70` completed `./scripts/bootstrap.ps1` with Python 3.13.15, uv 0.12.3, Node.js 24.19.0, Compose PostgreSQL, locked Python/npm dependencies, migrations, and Chromium. Tool-observed elapsed time was about 35 seconds. It then completed `./scripts/check.ps1` successfully. The disposable worktree is deliberately not a release artifact. |
| Standard matrix | `./scripts/check.ps1` passed on the EG-014 branch: publication/metadata/static-release checks, Compose validation, Ruff format/lint, mypy, 208 non-integration Python tests, web lint/unit/Chromium E2E/axe checks, and production web build. |
| PostgreSQL integration | `uv run --python 3.13.15 --locked pytest -m integration` passed with 14 isolated PostgreSQL tests. The suite creates and drops only a uniquely named test database. |
| Real retrieval | A fresh, secret-free `evalgate-evaluate --mode retrieval` run against index `6932f8da-e71b-533f-ae2b-4c969cd3acd2` passed `scripts/check_retrieval_baseline.py`. It covered 36 reviewed cases: precision@5 `0.144444`, recall@5/source coverage `0.722222`, MRR `0.604167`, and nDCG@5 `0.633985`. The local ignored artifact is `artifacts/retrieval-eg014-pre.json`; retrieval mode does not assess answer quality. |
| Retrieval-regression sensitivity | [EG-010](../backlog/EG-010-regression-gate.md) and `apps/api/tests/test_retrieval_baseline.py` retain the reviewed immutable baseline and test-only known-bad rejection. The current good run above passed; the known-bad fixture is intentionally rejected by the test. |
| Governed live generation | [Evaluation governance](../evaluation/README.md) links the reviewed EG-015 OpenRouter artifact and review record. It is negative/limitation-heavy evidence, not a quality-success claim: 72 repetitions, human pass and citation recall both `0.180556`, and only three valid advisory judge labels. The normal API/browser remains fixture-only. |
| Image, health, and shutdown | `./scripts/release_candidate.ps1` rebuilt the unchanged local `evalgate-api:0.9.0` definition, identified image ID `sha256:c6c86cc9c95d89935d1c7740c9e5ad9bb80e61f85ffca1062e6ccb50753c7222`, confirmed UID/GID `10001:10001`, liveness `alive`, readiness database `available`/migration `current`, and finite graceful stop. See [EG-013D evidence](EG-013D-release-candidate.md). |
| SBOM, publication, metadata | `./scripts/release_supply_chain.ps1` regenerated a CycloneDX SBOM with Docker SBOM. Publication and metadata checks passed. The SBOM is a local ignored artifact and has not been attached to a public release. |

The relevant machine-readable contracts are the versioned OpenAPI, stream, corpus, retrieval,
evaluation, prompt, and release schemas under `contracts/`. Accepted architecture decisions are
indexed in [ADRs](../adr/README.md); their application boundaries, PostgreSQL-only, hybrid
retrieval, reference embedding, SSE, evaluation, corpus, public-mode, deferred-hosting, and
OpenRouter decisions agree with the current R3 code and documentation.

## Release-blocking gaps

1. **Container vulnerability scan:** the current evidence is `waived_tool_unavailable`, not a
   scan. Install and run either Trivy or Grype locally, review every finding, and ensure no
   severity-critical or severity-high finding remains unresolved. A tool-availability waiver
   cannot be accepted for the first stable release.
2. **Manual accessibility review:** the [EG-013B record](../accessibility/EG-013B-manual-review.md)
   still has pending screen-reader checks, 200% zoom, and forced-colors/high-contrast review. A
   human reviewer must complete and date these rows before a WCAG-related release claim.
3. **Remote CI evidence:** the repository has a pinned, secret-free PR workflow, but no linked
   successful remote CI run is available in this local evidence record. Before publishing, record
   the successful run URL/commit and confirm its immutable retrieval artifact.
4. **Product experience manual review:** EG-017 implements the responsive, human-readable product
   shell and finite client recovery states. Its manual accessibility checks remain part of the
   manual-review gate above; no broader accessibility claim is made.
5. **Real-world showcase merge:** EG-018 is implemented and locally verified at `0.11.0` with a   pinned CC BY 4.0 Kubernetes source, reviewed 18-case dataset, repaired three-model comparison,
   explicit cost/failure evidence, and weak-quality limitations. It is not release evidence until
   this branch is reviewed and merged without changing the governed artifacts.
These are release blockers. The first three require evidence or review; the last two require their
separately scoped implementation branches. None authorizes a code or image-definition change on
this documentation branch.

## Security, privacy, operations, and limitations

- [Threat model](../security/threat-model.md) and [public-mode policy](../security/public-mode.md)
  show privileged-route denial, bounded content-free HTTP handling, no browser secret, no public
  content persistence, and exact provider-endpoint controls. They do not authorize deployment.
- [Operations evidence](../operations/EG-013C-observability-cost.md) documents bounded,
  content-free telemetry and process-local public-generation controls. Public live generation is
  still disabled; host-level limits, hosting, TLS, retention, region, and spend approval remain
  EG-016 decisions.
- [R3 runbooks](../runbooks/R3-operational-drills.md) cover shutdown, provider outage/cooldown,
  reset/restore, rollback, credential rotation, and kill switch. Previous-image rollback remains
  a documented recovery procedure, not a completed promotion drill, because no stable release
  digest exists yet.
- [NOTICE](../../NOTICE.md), [MIT license](../../LICENSE), CC0 corpus text, and the reference-model
  manifest establish code/corpus/model provenance boundaries. No model artifact is distributed.

## Version handoff and recommendation

Do **not** change `0.11.0` directly to `1.0.0`. Review/merge EG-018,
then independently evidence the scanner, manual-review, and remote-CI gates. Rerun the complete
matrix, update this record with every new artifact and disposition, and only then apply the
controlled final version bump described in [`docs/WORKFLOW.md`](../WORKFLOW.md). Rebuild the
unchanged accepted image as `1.0.0`, regenerate its smoke/SBOM/scan/digest evidence, and prepare a
final release record. No tag, release, push, or deployment is authorized by this record.
