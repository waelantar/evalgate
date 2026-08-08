# EG-003: PostgreSQL/pgvector schema and migrations

- Status: Planned
- Branch: `feat/eg-003-postgres-schema`
- Depends on: EG-002 merged to `main` with the accepted reference embedding identity and 384-dimensional decision
- Release: R1
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

> Work only on EG-003 on branch `feat/eg-003-postgres-schema`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0002, ADR-0004, and this story. Confirm EG-002 and its verified reference embedding manifest are on clean `main`. Implement the reviewed PostgreSQL/pgvector schema with a literal 384-dimensional column, separate corpus/index versions, constraints, migration-aware readiness, and real PostgreSQL tests. Do not add corpus content, embedding, search, generation, or SQLite. Do not merge, push, deploy, or start EG-004. Stop on any schema-decision conflict. Finish with an ER/migration explanation, changed files, exact test evidence, rollback/reset behavior, residual risk, and suggested commit message.
