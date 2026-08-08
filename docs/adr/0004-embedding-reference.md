# ADR-0004: Local 384-dimensional reference embedding

- Status: Accepted with verification gate
- Date: 2026-08-08
- Story: EG-002

## Context

Pull-request retrieval evidence must not require a paid secret. Schema width and index identity must remain reproducible.

## Decision

Use FastEmbed with `BAAI/bge-small-en-v1.5` and a literal `vector(384)` schema. EG-002 must verify and record the exact model revision, artifact checksum, license, FastEmbed/ONNX Runtime versions, query/passage policy, and numeric tolerances before EG-003/EG-004 rely on it.

## Consequences

CI may download/cache a public model but cannot silently substitute deterministic vectors. A dimension change creates a new index version and reviewed migration/reset path.

## Verification

Dimension/license/checksum contract test and repeatability evidence on declared environments.
