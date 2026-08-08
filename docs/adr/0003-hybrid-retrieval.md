# ADR-0003: Exact hybrid retrieval with reciprocal-rank fusion

- Status: Accepted
- Date: 2026-08-08
- Story: EG-005

## Context

The initial corpus is small, while lexical and semantic queries have different strengths. Raw component scores are not directly comparable.

## Decision

Rank lexical candidates with PostgreSQL `tsvector` and `ts_rank_cd`, rank exact cosine candidates with pgvector, and fuse ranks with versioned RRF and deterministic tie-breaking. Do not call PostgreSQL full-text ranking BM25. Do not add HNSW or a reranker initially.

## Consequences

Every result can expose component ranks and RRF score. Approximate indexing requires measured latency pressure and a recall comparison.

## Verification

Lexical-only, vector-only, and hybrid ablations plus stable-ranking property tests.
