# EG-004: Governed corpus and idempotent ingestion

- Status: Implemented, merged, and locally verified; remote CI pending
- Branch: `feat/eg-004-governed-corpus`
- Depends on: EG-002 and EG-003 merged to `main`
- Release: R2
- Version action: Minor `0.1.2 -> 0.2.0`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: G-01, FR-01, NFR-03, ADR-0007

## Outcome

The original Northstar Operations Handbook is licensed, manifested, chunked, embedded through the accepted reference adapter, and ingested idempotently as a declared corpus/index version.

## Scope

- Add and ratify full CC0-1.0 corpus legal text before content.
- Author 15-25 coherent technical documents with version conflicts, hard negatives, unanswerable material, citation traps, and indirect-injection fixtures.
- Validate manifest/path/license/hash/provenance, normalize text, record source offsets/sections, and create versioned chunks.
- CLI/local-admin ingestion by declared bundled corpus key only, with transactional idempotency and structured report.

## Non-goals

- URL/path input from callers, uploads, external corpus fetch, golden questions, retrieval API, or public ingestion.

## Acceptance evidence

- [x] License and manifest validation pass; publication/privacy review finds no third-party or personal content.
- [x] Two identical ingestions create no duplicate corpus/index/document/chunk rows.
- [x] A content, chunking, or embedding identity change creates a new version rather than mutating evidence.
- [x] Failure rolls back transactionally and reports a typed non-sensitive error.

## Verification evidence

Local verification on 2026-08-29 used Python 3.13.15, uv 0.12.3, Node.js 24.19.0,
FastEmbed 0.8.0, ONNX Runtime 1.29.0, PostgreSQL 18, and pgvector 0.8.5.

- Publication/privacy and metadata checks passed for 160 text files; Ruff formatting/lint and
  strict mypy passed.
- 47 unit/contract tests, 7 real-PostgreSQL integration tests, and 2 web tests passed; frontend
  lint and the production build also passed.
- The 20-document CC0 corpus produced 161 reconstructive H2 chunks. The verified pinned BGE
  runtime reported 24-63 tokens per chunk and generated finite 384-dimensional vectors.
- Integration evidence covers created then `already_present` ingestion, document reuse across
  changed index identity, a side-by-side content version, immutable-evidence tamper rejection,
  and trigger-induced transactional rollback in disposable databases.
- Remote GitHub Actions execution remains pending; this branch is not released or deployed.

## Required tests and review

- Manifest/license/privacy validation, chunk/source-offset tests, transaction/idempotency integration tests, failure rollback, and manual corpus-content review.

## Expected file ownership

- `data/corpus/`, `data/manifests/`, corpus legal text, ingestion/chunking application code and adapters, CLI entrypoint, and ingestion tests.

## Stop conditions

- Corpus license is not ratified, source content is copied, or ingestion needs an arbitrary URL/path.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.1.2` on the latest accepted `main`, apply only the declared minor bump to `0.2.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-004 on branch `feat/eg-004-governed-corpus`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0004, ADR-0007, the corpus schema, and this story. Confirm EG-002 and EG-003 are merged to clean `main`. Add the full approved CC0 text, author and review the bounded synthetic corpus, validate its immutable manifest, and implement declared-source transactional idempotent ingestion with source-offset evidence. Do not build search, answers, golden evaluation, uploads, or URL ingestion. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, call a paid provider, tag/release, or start another story. Stop on license/provenance or identity changes. Finish with corpus rationale, data flow, files, exact evidence, failure/rollback behavior, limitations, version handoff, and suggested commit message.
