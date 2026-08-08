# ADR-0001: Framework-independent application core

- Status: Accepted
- Date: 2026-08-08
- Story: EG-002

## Context

HTTP, CLI evaluation, and later MCP must execute the same retrieval and answer rules without coupling the product to one transport or SDK.

## Decision

`domain` owns values/invariants and imports no framework. `application` owns use cases and ports and may import only `domain`. PostgreSQL, embedding, and generation are outbound adapters. HTTP, CLI, and MCP are independent inbound adapters.

## Consequences

The design adds interfaces and mapping code but makes contracts testable and prevents FastAPI or MCP lifecycle state from becoming application state.

## Verification

Architecture import tests run in CI. Any cross-boundary exception requires a superseding ADR.
