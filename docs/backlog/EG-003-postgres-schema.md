# EG-003: PostgreSQL/pgvector schema and migrations

- Status: Planned
- Branch: `feat/eg-003-postgres-schema`
- Depends on: EG-002 merged to `main` with the accepted reference embedding identity and 384-dimensional decision
- Release: R1
- Version action: Patch `0.1.1 -> 0.1.2`
- Codex profile: `gpt-5.6-sol` with `medium` reasoning
- Blueprint requirements: NFR-02, NFR-10, ADR-0002, ADR-0004

## Outcome

PostgreSQL has a reviewed, reversible foundation schema that separates immutable corpus versions from derived index versions and reports database plus migration readiness.

## Scope

- Alembic revision enabling pgvector and creating corpus/index/document/chunk/evaluation tables from the blueprint ER model.
- Literal `vector(384)`, source offsets, stable hashes, foreign keys, checks, and uniqueness constraints.
- Async SQLAlchemy mappings/repositories only where required to prove schema wiring.
- Migration-head readiness, clean reset/seed-empty commands, and real PostgreSQL migration tests.

## Non-goals

- Corpus rows, embedding calls, retrieval queries, fixture data represented as a corpus, or SQLite tests.

## Acceptance evidence

- [ ] Upgrade from empty database reaches one expected head; schema constraints are inspected in tests.
- [ ] Re-running upgrade is safe and reset instructions reproduce an empty ready database.
- [ ] Readiness is false on database/migration mismatch and contains no secret.
- [ ] Tests use the pinned PostgreSQL/pgvector image, never SQLite.

## Required tests and review

- Real PostgreSQL migration/constraint/readiness/reset tests, schema inspection, idempotent upgrade, and recovery review.

## Expected file ownership

- `apps/api/migrations/`, PostgreSQL mappings/adapters, readiness wiring, database integration tests, and explicit reset/seed-empty scripts/docs.

## Stop conditions

- Any runtime-configured vector dimension, destructive default command, second database, or change to source/index identity.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.1.1` on the latest accepted `main`, apply only the declared patch to `0.1.2` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-003 on branch `feat/eg-003-postgres-schema`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0002, ADR-0004, and this story. Confirm EG-002 and its verified reference embedding manifest are on clean `main`. Implement the reviewed PostgreSQL/pgvector schema with a literal 384-dimensional column, separate corpus/index versions, constraints, migration-aware readiness, and real PostgreSQL tests. Do not add corpus content, embedding, search, generation, or SQLite. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, tag/release, or start EG-004. Stop on any schema-decision conflict. Finish with an ER/migration explanation, changed files, exact test evidence, rollback/reset behavior, residual risk, version handoff, and suggested commit message.
