# EG-005: Explainable hybrid retrieval

- Status: Planned
- Branch: `feat/eg-005-hybrid-retrieval`
- Depends on: EG-004 merged to `main`
- Release: R2
- Version action: Minor `0.2.0 -> 0.3.0`
- Codex profile: `gpt-5.6-sol` with `medium` reasoning
- Blueprint requirements: G-02, FR-02, CON-03, ADR-0003

## Outcome

A bounded `POST /api/v1/search` returns stable evidence with source/index versions, lexical rank, vector rank, RRF score, and deterministic tie-breaking.

## Scope

- Framework-free search use case and PostgreSQL lexical/exact-vector adapter queries.
- Versioned RRF configuration and result/evidence types.
- Bounded request/response OpenAPI and Problem Details contracts.
- Query/body privacy rules and lexical-only, vector-only, hybrid ablation command.

## Non-goals

- BM25 claims, score normalization/addition, HNSW, reranking, answer generation, chat history, or URL query parameters.

## Acceptance evidence

- [ ] Real PostgreSQL tests prove lexical, vector, fusion, filters, empty/no-match, invalid index, and stable ties.
- [ ] Result evidence includes both corpus and index identity plus component ranks.
- [ ] Search body/query content is absent from access/application logs.
- [ ] Exact search performance is measured on the reference corpus; no unsupported performance promise is made.

## Required tests and review

- Run real PostgreSQL lexical, exact-vector, hybrid, filtering, no-match, invalid-version, stable-tie, logging-privacy, and ablation tests; review RRF math and measured performance.

## Expected file ownership

- Search domain/application types, PostgreSQL retrieval adapter, `POST /api/v1/search` OpenAPI/HTTP adapter, retrieval tests, ablation command, and retrieval documentation.

## Stop conditions

- A new retrieval engine/index/reranker, raw-score fusion, or contract change to source/index identity is proposed.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.2.0` on the latest accepted `main`, apply only the declared minor bump to `0.3.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-005 on branch `feat/eg-005-hybrid-retrieval`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0003, the accepted corpus/index schema, and this story. Confirm EG-004 is merged to clean `main`. Implement bounded POST search using PostgreSQL `ts_rank_cd`, exact cosine pgvector search, versioned RRF, explainable component ranks, stable ties, typed errors, and real database tests/ablations. Do not call it BM25, add HNSW/reranking, generate answers, or place queries in URLs/logs. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, tag/release, or start EG-006. Finish with retrieval math/query explanation, changed files, exact evidence/measurements, limitations, version handoff, and suggested commit message.
