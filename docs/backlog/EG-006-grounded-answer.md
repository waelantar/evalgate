# EG-006: Grounded answer core and validated citations

- Status: Implemented, locally verified, reviewed, and manually merged
- Branch: `feat/eg-006-grounded-answer`
- Depends on: EG-005 merged to `main`
- Release: R2
- Version action: Patch `0.3.0 -> 0.3.1`
- Codex profile: `gpt-5.6-sol` with `medium` reasoning
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

- [x] Unit/contract tests cover supported, multi-evidence, unanswerable, missing/spoofed citation, malformed provider output, timeout, cancellation, and explicit mode selection.
- [x] A provider cannot inject source metadata or quote text.
- [x] Prompt/evidence content is absent from logs and errors.
- [x] Fixture failure never silently becomes a success or live response.

## Verification evidence

Local verification on 2026-08-30 used Windows, Python 3.13.15, uv 0.12.3, and Node.js
24.19.0.

- The pre-bump repository gate passed publication and metadata validation, Ruff formatting and
  lint, strict mypy across 47 source files, 126 non-integration API tests, 2 web tests, frontend
  lint, and the production web build.
- The complete post-bump gate passed the same checks with synchronized product version `0.3.1`;
  publication validation covered 181 text files.
- The focused grounded-answer, contract, and provider-port run passed 29 tests.
- Tests cover supported and multi-evidence answers, insufficient support, missing and spoofed
  citations, strict provider-output shape, metadata injection, evidence integrity, bounded
  context and quotes, explicit modes, timeout, cancellation cleanup, redaction, and deterministic
  fixture identity.
- No live provider was called. EG-006 adds no HTTP answer endpoint, persistence, streaming,
  quality metric, deployment, or release claim; remote GitHub Actions execution remains pending.

## Required tests and review

- Run answer-use-case and generation-port contract tests for supported, multi-evidence, unanswerable, spoofed/missing citation, malformed output, timeout, cancellation, redaction, and explicit-mode cases; review prompt and citation trust boundaries.

## Expected file ownership

- Answer domain/application policy, versioned prompt assets, generation-port contracts, explicit fixture adapter, citation-validation code, typed errors, and focused unit/contract tests.

## Stop conditions

- A live provider, tool, persistence policy, prompt framework, or citation representation differs from the accepted contract.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.3.0` on the latest accepted `main`, apply only the declared patch to `0.3.1` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-006 on branch `feat/eg-006-grounded-answer`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0001, ADR-0006, the search contract, and this story. Confirm EG-005 is merged to clean `main`. Implement the framework-free grounded-answer use case with bounded retrieved evidence, versioned prompt policy, explicit provider mode, evidence-ID-only model output, server-derived citations, and typed failure tests. Do not add HTTP streaming, UI, live provider calls, tools, or content persistence. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, spend, tag/release, or start EG-007. Finish with prompt/citation data-flow explanation, files, exact tests, threat/residual-risk notes, version handoff, and suggested commit message.
