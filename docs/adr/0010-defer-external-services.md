# ADR-0010: Defer provider and host selection

- Status: Accepted
- Date: 2026-08-08
- Stories: EG-015, EG-016

## Context

Provider models, retention terms, regions, prices, streaming behavior, and hosting capabilities change. Selecting them before their release gate creates stale or unapproved commitments.

## Decision

Foundation and PR CI use no live provider and select no cloud. EG-015 verifies one generation/judge strategy under an approved budget. EG-016 separately verifies one host, region, access posture, streaming path, secret handling, cost, rollback, and retention before optional deployment.

## Consequences

The core remains portable and no setup action spends money or creates external state.

## Verification

Primary-source decision record, approved limits, protected configuration, artifact evidence, and deployment smoke/rollback drill.
