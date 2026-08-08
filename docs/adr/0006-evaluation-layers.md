# ADR-0006: Three separate assurance layers

- Status: Accepted
- Date: 2026-08-08
- Stories: EG-009, EG-010, EG-015

## Context

Deterministic fixtures, real local retrieval, and hosted generation answer different questions and have different reproducibility, privacy, cost, and secret requirements.

## Decision

Use fixture contract tests for software mechanics, repeatable real-embedding retrieval evaluation for PR regression evidence, and a protected manual/scheduled live-generation suite for answer-quality evidence. Live judge metrics remain advisory until calibrated against human labels.

## Consequences

CI stays secret-free. Fixture scores cannot support quality claims, and baselines require reviewed artifact diffs.

## Verification

A seeded bad retrieval change must fail the calibrated gate; a governed live artifact must record versions, variance, human review, and limitations.
