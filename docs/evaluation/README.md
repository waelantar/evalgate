# Evaluation governance and results

EG-009 owns the 36-case reviewed golden set and deterministic metric artifact. EG-010 owns the
reviewed retrieval baseline and secret-free PR comparison. EG-011 imports an explicitly approved
artifact into bounded PostgreSQL projections and exposes read-only run/detail/case views. EG-015
owns protected live-generation evidence. CI artifacts never write to application state, and no
baseline or review record is updated automatically.

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

## Governed live generation

The EG-015 live suite uses only the approved OpenRouter `deepseek/deepseek-v4-flash` path, with a
USD 4.60 hard budget and USD 4.14 stop limit. The key must be supplied as
`EVALGATE_OPENROUTER_API_KEY` from a local ignored `.env` file or the protected GitHub secret of the
same name. Do not place the key in source files, examples, command history screenshots, or browser
configuration.

Local PowerShell setup for the protected live run:

```powershell
$env:EVALGATE_ENVIRONMENT = "local"
$env:EVALGATE_EMBEDDING_MODE = "reference"
$env:EVALGATE_GENERATION_MODE = "live"
$env:EVALGATE_REFERENCE_EMBEDDING_SNAPSHOT = ".evalgate-cache/reference-embedding/snapshot"
$env:EVALGATE_LIVE_PROVIDER = "openrouter"
$env:EVALGATE_OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
$env:EVALGATE_LIVE_EVAL_BUDGET_USD = "4.60"
$env:EVALGATE_LIVE_EVAL_STOP_USD = "4.14"
```

Then run:

```powershell
uv run --python 3.13.15 --project apps/api --locked evalgate-live-evaluate `
  --index-version 6932f8da-e71b-533f-ae2b-4c969cd3acd2 `
  --output artifacts/evaluation-live-openrouter.json `
  --markdown artifacts/evaluation-live-openrouter.md `
  --repetitions 2
```

The artifact is generation evidence, not a retrieval baseline and not an importable results DB row.
It records case/repetition IDs, status, cited evidence IDs, human labels, advisory judge labels,
usage, cost, agreement, and limitations. It deliberately excludes prompts, raw completions, corpus
text, provider secrets, and browser-visible configuration.

Reviewed local run `golden-1.0.0-openrouter-deepseek-v4-flash` completed on 2026-09-11 against
EvalGate 0.8.0 with 36 reviewed cases and two repetitions per case. The artifact-reported cost was
USD 0.004046, under the USD 4.14 stop limit. Human pass rate and citation recall were both
0.180556. The run is honest negative/limited evidence for this provider posture: most failures were
malformed output, provider timeout, or provider unavailable, and only three repetitions reached a
valid advisory judge label.
