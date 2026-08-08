# ADR-0002: PostgreSQL and pgvector in every environment

- Status: Accepted
- Date: 2026-08-08
- Story: EG-003

## Context

Lexical ranking, vector queries, migrations, transactions, and generated columns are product behavior. A substitute test database would hide incompatibilities.

## Decision

Use PostgreSQL 18 with pgvector 0.8.5 locally, in integration tests, in CI, and in any deployment. Do not add SQLite.

## Consequences

Integration tests require a container, but database behavior has environment parity. Image tags and release digests are recorded.

## Verification

Migration, reset, readiness, lexical, and vector integration tests run against PostgreSQL.
