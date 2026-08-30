# ADR-0003: Exact hybrid retrieval with reciprocal-rank fusion

- Status: Accepted
- Date: 2026-08-08
- Story: EG-005

## Context

The initial corpus is small, while lexical and semantic queries have different strengths. Raw component scores are not directly comparable.

## Decision

Rank lexical candidates with PostgreSQL `tsvector` and `ts_rank_cd`, rank exact cosine candidates with pgvector, and fuse ranks with versioned RRF and deterministic tie-breaking. Do not call PostgreSQL full-text ranking BM25. Do not add HNSW or a reranker initially.

The first accepted policy is `hybrid-rrf-v1`, recorded independently from the
stored-index policy in `contracts/retrieval/hybrid-rrf-v1.json`. Keeping these
identities separate allows the same immutable index to be evaluated under a
different reviewed fusion policy without changing its deterministic index UUID.

`hybrid-rrf-v1` uses independently ranked lexical and vector candidate lists of
depth 50. Lexical retrieval uses
`plainto_tsquery('pg_catalog.simple', query)` and orders `ts_rank_cd` descending;
vector retrieval uses exact cosine distance and orders distance ascending. Each
component uses the evidence UUID ascending as its final tie-break and assigns
one-based ranks. For evidence `d`, fusion uses:

```text
rrf(d) = present(lexical) / (60 + lexical_rank(d))
       + present(vector)  / (60 + vector_rank(d))
```

A missing component contributes zero and is reported with a null rank. Fused
results order by RRF score descending and then evidence UUID ascending. Raw
component scores are neither fused nor exposed. No similarity threshold is
applied, so no-match behavior belongs to lexical-only ablation or an empty
selected index; exact-vector and hybrid retrieval over a populated index return
the bounded nearest candidates.

The HTTP input selects the deterministic `index_versions.id` UUID emitted by
ingestion. Responses also report the human-readable `index_key`, the complete
source-corpus identity, and the index configuration hashes and embedding
identity needed to explain which stored evidence was searched.

The policy pins the lexical configuration identity to the SHA-256 of
`postgresql-tsvector:pg_catalog.simple`:
`4434b9362573450f668ed0014f428e744d3a7cc30f4630ebafedb22708b7d786`.
Search rejects a selected index whose stored lexical-configuration hash differs
from the policy before any candidate query. It likewise rejects an embedding
model, revision, checksum, or dimension mismatch. These are typed retrieval
configuration failures rather than an empty result.

## Consequences

Every result can expose component ranks and RRF score. Approximate indexing requires measured latency pressure and a recall comparison.

## Verification

Lexical-only, vector-only, and hybrid ablations plus stable-ranking property tests.
Contract tests additionally cover request bounds, selected-index isolation,
typed Problem Details, and omission of query and chunk content from logs.
