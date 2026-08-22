# ADR-0002: PostgreSQL and pgvector in every environment

- Status: Accepted
- Date: 2026-08-08
- Story: EG-003

## Context

Lexical ranking, vector queries, migrations, transactions, and generated columns are product behavior. A substitute test database would hide incompatibilities.

## Decision

Use PostgreSQL 18 with pgvector 0.8.5 locally, in integration tests, in CI, and in any deployment. Do not add SQLite.

Pin the container by the reviewed multi-platform registry digest. The foundation schema uses
denormalized parent keys with composite foreign keys for two integrity boundaries: a chunk's
document and index must belong to the same corpus version, and an evaluation case result's run
and case must belong to the same evaluation dataset. PostgreSQL constraints, rather than
application convention or triggers, enforce both invariants.

The chunk `search_vector` column is stored and non-generated. EG-004 must populate it using the
index version's reviewed lexical configuration; the foundation migration does not silently
select `english`, `simple`, or another PostgreSQL text-search configuration.

## Consequences

Integration tests require a container, but database behavior has environment parity. Image tags and release digests are recorded.

## Verification

Migration, reset, readiness, lexical, and vector integration tests run against PostgreSQL. The
EG-003 image identity is
`pgvector/pgvector:0.8.5-pg18-trixie@sha256:9d2e61c7352b9e9f4798df5fd9a498f043f4cda1cdacc707de3d198650f4321e`.
