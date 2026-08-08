# EG-004: Governed corpus and idempotent ingestion

- Status: Planned
- Branch: `feat/eg-004-governed-corpus`
- Depends on: EG-002 and EG-003 merged to `main`
- Release: R2
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

- [ ] License and manifest validation pass; publication/privacy review finds no third-party or personal content.
- [ ] Two identical ingestions create no duplicate corpus/index/document/chunk rows.
- [ ] A content, chunking, or embedding identity change creates a new version rather than mutating evidence.
- [ ] Failure rolls back transactionally and reports a typed non-sensitive error.

## Required tests and review

- Manifest/license/privacy validation, chunk/source-offset tests, transaction/idempotency integration tests, failure rollback, and manual corpus-content review.

## Expected file ownership

- `data/corpus/`, `data/manifests/`, corpus legal text, ingestion/chunking application code and adapters, CLI entrypoint, and ingestion tests.

## Stop conditions

- Corpus license is not ratified, source content is copied, or ingestion needs an arbitrary URL/path.

## Copy-paste coding-agent brief

> Work only on EG-004 on branch `feat/eg-004-governed-corpus`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0004, ADR-0007, the corpus schema, and this story. Confirm EG-002 and EG-003 are merged to clean `main`. Add the full approved CC0 text, author and review the bounded synthetic corpus, validate its immutable manifest, and implement declared-source transactional idempotent ingestion with source-offset evidence. Do not build search, answers, golden evaluation, uploads, or URL ingestion. Do not merge, push, deploy, or call a paid provider. Stop on license/provenance or identity changes. Finish with corpus rationale, data flow, files, exact evidence, failure/rollback behavior, limitations, and suggested commit message.
