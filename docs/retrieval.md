# Explainable retrieval

EG-005 exposes one bounded public search operation and one local diagnostic over the same
framework-free application use case. The accepted decisions live in
[ADR-0003](adr/0003-hybrid-retrieval.md), the machine-readable policy is
[`hybrid-rrf-v1`](../contracts/retrieval/hybrid-rrf-v1.json), and the HTTP schema is the checked-in
[OpenAPI contract](../contracts/openapi/foundation.yaml).

## Request and evidence flow

`POST /api/v1/search` accepts `query`, the deterministic ingestion-produced `index_version` UUID,
and an optional result `limit` from 1 through 20. The API normalizes the bounded query, verifies
that the selected index matches the pinned lexical and embedding identities, embeds the query,
runs independent PostgreSQL lexical and exact-vector searches, and fuses their ranks. Each result
returns content and provenance together with stable evidence/document IDs, complete source-corpus
and derived-index identities, nullable component ranks, and the fused score.

Queries are JSON-body data, never URL parameters. Uvicorn access logging is disabled, application
errors are content-free, and the diagnostic reads its query only from standard input. The
diagnostic JSON contains identities, evidence IDs, ranks, scores, timings, and limitations; it
does not emit the query or chunk content.

## Retrieval policy

`hybrid-rrf-v1` independently selects up to 50 lexical and 50 vector candidates:

- lexical: `plainto_tsquery('pg_catalog.simple', query)` with `ts_rank_cd` descending;
- vector: exact pgvector cosine distance ascending over the fixed 384-dimensional embedding;
- component ties: evidence UUID ascending;
- component ranks: one-based;
- fusion ties: RRF score descending, then evidence UUID ascending.

For evidence `d`, the fused score is:

```text
rrf(d) = present(lexical) / (60 + lexical_rank(d))
       + present(vector)  / (60 + vector_rank(d))
```

A missing component contributes zero and its rank is `null`. Raw lexical/vector scores are not
combined or exposed. This is PostgreSQL full-text ranking, not BM25. No similarity threshold is
applied: exact vector or hybrid retrieval over a populated index returns the bounded nearest
candidates, while lexical-only ablation or an empty selected index demonstrates no-match behavior.

## Local ablation

Configure explicit reference embedding mode, the verified local snapshot, and the PostgreSQL URL.
Then pipe one private query to the diagnostic:

```powershell
$env:EVALGATE_EMBEDDING_MODE = "reference"
$env:EVALGATE_REFERENCE_EMBEDDING_SNAPSHOT = ".evalgate-cache/reference-embedding/snapshot"
"status ledger recovery" | uv run --python 3.13.15 --project apps/api --locked evalgate-retrieval-ablation `
  --index-version <INDEX_VERSION_UUID> --warmups 5 --repetitions 30 --limit 10
```

The default run reports lexical, vector, and hybrid modes. Repeated timings are observations on the
declared runtime and corpus, not service-level objectives. This diagnostic does not calculate
precision, recall, MRR, nDCG, thresholds, or a reviewed baseline.

## Failure and recovery boundaries

Invalid requests, missing indexes, identity/configuration mismatches, invalid adapter output, and
unavailable dependencies map to stable Problem Details codes without request content. Retrieval is
read-only and creates no rollback state; rollback is the normal reviewed application rollback, and
the immutable governed corpus/index remains available to the predecessor application version.
