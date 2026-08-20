# EG-002: Provider-neutral ports and reference embedding decision

- Status: Planned
- Branch: `feat/eg-002-provider-ports`
- Depends on: EG-001 merged to `main`
- Release: R1
- Version action: Patch `0.1.0 -> 0.1.1`
- Codex profile: `gpt-5.6-terra` with `medium` reasoning
- Blueprint requirements: NFR-01, NFR-03, ADR-0001, ADR-0004

## Outcome

The application layer defines typed embedding, generation, clock, and identity ports with explicit modes, deterministic test fixtures, and a verified reference-embedding manifest; no use case silently falls back between modes.

## Scope

- Domain/application value types and async ports independent of frameworks/SDKs.
- Typed configuration that rejects invalid public/live combinations.
- Explicit fixture embedding/generation adapters for mechanics tests only.
- Verify BGE model license, exact revision/checksum, 384 dimensions, FastEmbed/ONNX versions, prefixes, cache behavior, and numeric tolerances in a committed manifest/ADR update.

## Non-goals

- Database schema, model download in every unit test, ingestion, retrieval, prompt, live provider SDK, or provider call.

## Acceptance evidence

- [ ] Import-boundary test covers all new application modules.
- [ ] Port/fixture contract tests prove stable outputs and explicit mode selection.
- [ ] Missing or failed live configuration returns a typed configuration error, never fixture output.
- [ ] Reference embedding manifest is license/revision/checksum reviewed.

## Required tests and review

- Unit and port-contract tests, architecture import checks, configuration failure tests, manifest/license/checksum review, and repeatability smoke evidence.

## Expected file ownership

- `apps/api/src/evalgate/domain/`, `application/`, explicit fixture adapters, typed configuration, provider-port tests, embedding manifest, and ADR-0004 update.

## Stop conditions

- Model license/revision/dimension cannot be verified.
- A different embedding model, dimension, provider, or framework is proposed.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-terra`, reasoning effort `medium`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.1.0` on the latest accepted `main`, apply only the declared patch to `0.1.1` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-002 on branch `feat/eg-002-provider-ports`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0001, ADR-0004, and this story. Confirm EG-001 is on a clean `main`, then create the exact branch. Define framework-free typed ports and explicitly labeled deterministic fixtures; verify and record the BGE reference metadata without implementing ingestion, retrieval, persistence, or any live provider call. Add boundary and contract tests. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, spend, tag/release, or begin EG-003. Stop if the model decision changes. Finish with a design explanation, changed files, acceptance mapping, exact commands/results, residual risk, version handoff, and suggested commit message.
