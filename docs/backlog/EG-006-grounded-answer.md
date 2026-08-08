# EG-006: Grounded answer core and validated citations

- Status: Planned
- Branch: `feat/eg-006-grounded-answer`
- Depends on: EG-005 merged to `main`
- Release: R2
- Blueprint requirements: FR-03, FR-12, NFR-01, NFR-05

## Outcome

The application core retrieves bounded evidence, invokes an explicitly selected generation port, and returns an answer whose evidence IDs are validated and enriched server-side.

## Scope

- Versioned prompt policy separating system rules, question, and untrusted evidence.
- Answer use case over search and generation ports with token/context budgets.
- Model output schema containing answer text plus evidence IDs only.
- Server validation of retrieval membership and derivation of source, span hash, and bounded quote.
- Explicit fixture and retrieval-only behavior; typed provider/validation errors.

## Non-goals

- HTTP streaming, browser UI, live-provider selection/call, tools/agent loop, semantic judge, or persisted public questions/answers.

## Acceptance evidence

- [ ] Unit/contract tests cover supported, multi-evidence, unanswerable, missing/spoofed citation, malformed provider output, timeout, and explicit mode selection.
- [ ] A provider cannot inject source metadata or quote text.
- [ ] Prompt/evidence content is absent from logs and errors.
- [ ] Fixture failure never silently becomes a success or live response.

## Required tests and review

- Run answer-use-case and generation-port contract tests for supported, multi-evidence, unanswerable, spoofed/missing citation, malformed output, timeout, cancellation, redaction, and explicit-mode cases; review prompt and citation trust boundaries.

## Expected file ownership

- Answer domain/application policy, versioned prompt assets, generation-port contracts, explicit fixture adapter, citation-validation code, typed errors, and focused unit/contract tests.

## Stop conditions

- A live provider, tool, persistence policy, prompt framework, or citation representation differs from the accepted contract.

## Copy-paste coding-agent brief

> Work only on EG-006 on branch `feat/eg-006-grounded-answer`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0001, ADR-0006, the search contract, and this story. Confirm EG-005 is merged to clean `main`. Implement the framework-free grounded-answer use case with bounded retrieved evidence, versioned prompt policy, explicit provider mode, evidence-ID-only model output, server-derived citations, and typed failure tests. Do not add HTTP streaming, UI, live provider calls, tools, or content persistence. Do not merge, push, deploy, spend, or start EG-007. Finish with prompt/citation data-flow explanation, files, exact tests, threat/residual-risk notes, and suggested commit message.
