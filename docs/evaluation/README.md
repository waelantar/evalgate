# Evaluation governance and results

EG-009 owns the 36-case reviewed golden set and deterministic metric artifact. EG-010 owns the
reviewed retrieval baseline and secret-free PR comparison. EG-011 imports an explicitly approved
artifact into bounded PostgreSQL projections and exposes read-only run/detail/case views. EG-015
owns any future protected live-generation evidence. CI artifacts never write to application state,
and no baseline or review record is updated automatically.

## Import trust boundary

`evalgate-import-results` works only when `EVALGATE_ENVIRONMENT=local`. It rejects CI and public
mode before reading an artifact. A successful import requires all of the following:

- the artifact is at most 1 MB, matches `artifact.schema.json`, and contains at most 100 cases with
  at most 20 retrieved/relevant evidence IDs per case;
- a separate schema-valid approval record pins the exact artifact and dataset SHA-256 values;
- the complete dataset bytes match the artifact identity, every dataset case is reviewed, and the
  artifact case set and relevant-evidence labels match it exactly;
- the referenced index exists and its immutable corpus checksum matches the artifact;
- retrieval artifacts use the accepted `hybrid-rrf-v1` policy; and
- an existing run key is either the exact same artifact (idempotent success) or a rejected conflict.

Validation precedes persistence. Dataset, canonical case, run, and case-result writes then share one
database transaction. A failure rolls back the new run and all of its results. PostgreSQL stores only
the bounded manifest/metric/limitation projection and evidence ID arrays; it never duplicates the raw
artifact or corpus content.

For the reviewed local EG-009 artifact:

```powershell
uv run --python 3.13.15 --project apps/api --locked evalgate-import-results `
  --artifact artifacts/evaluation-retrieval.json `
  --review-record docs/evaluation/reviews/golden-v1-hybrid.json
```

The corpus/index referenced by the artifact must already be ingested. `imported` means new data was
committed; `already_imported` means the identical artifact was already present. To recover from a
rejected import, correct the artifact, dataset, review record, or referenced index and retry; no
partial run needs cleanup.

## Read-only inspection

The API exposes cursor-bounded `GET /api/v1/evaluation-runs`, run detail with optional `compare_to`,
and cursor/status-bounded case results. There is no HTTP import or evaluation-trigger route. The web
workbench displays immutable version identity, metrics and optional deltas, limitations, and the
retrieved versus reviewed evidence IDs for passed or failed cases. It includes loading, empty,
failure, and retry states and treats every stored string as plain React text.

Run unit/component checks with `./scripts/check.ps1`. Bootstrap installs the pinned Chromium build;
`npm --prefix apps/web run test:e2e` executes loaded/empty/error browser flows and an axe scan.
