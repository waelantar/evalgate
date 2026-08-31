# EG-009: Golden dataset and retrieval evaluation

- Status: In progress; fixture artifact and real retrieval ablation verified
- Branch: `feat/eg-009-golden-evaluation`
- Depends on: EG-005 and EG-006 merged to `main`
- Release: R2
- Version action: Minor `0.5.0 -> 0.6.0`
- Codex profile: `gpt-5.5` with `high` reasoning
- Blueprint requirements: G-04, FR-06, NFR-03, ADR-0006

## Outcome

A versioned 36-case dataset and CLI produce schema-valid JSON plus readable retrieval/citation evidence for an exact code, corpus, index, and policy identity.

## Scope

- Author 18 development, 6 judge-calibration seed/smoke, and 12 governed regression cases with reference facts, stable document/span evidence, tags, rationale, and review state.
- Implement precision@k, recall@k, MRR, nDCG@k, citation validity/support/coverage, source coverage, and unsupported-claim plumbing with tested definitions.
- Evaluation CLI, lexical/vector/hybrid ablations, environment/version manifest, numeric tolerance, JSON and Markdown artifact renderers.
- Record limitations; keep human/judge answer scoring unimplemented or explicitly advisory fixtures.

## Non-goals

- Active PR thresholds, automatic baseline, live provider/judge calls, secret holdout claims, results database/UI, or RAGAS dependency.

## Acceptance evidence

- [ ] Metric fixture/property tests cover zero denominators, ties, multi-evidence, unanswerable cases, and invalid citations.
- [x] Real PostgreSQL and pinned embedding retrieval identity is repeatable across two runs; timing tolerance remains observational and is not a release threshold.
- [ ] Artifacts validate against schema and record every required version/environment field.
- [ ] Splits and case edits have review/provenance; six calibration cases are not treated as sufficient judge authorization.

## Local verification evidence

- PostgreSQL/pgvector Compose service was healthy and migrations were applied.
- `evalgate-ingest --corpus northstar-operations` confirmed the governed 20-document, 161-chunk index was already present.
- Two `evalgate-retrieval-ablation` runs used index `6932f8da-e71b-533f-ae2b-4c969cd3acd2`, the pinned 384-dimensional BGE snapshot, and identical query/limits; hybrid evidence IDs matched exactly.
- Reports are local-only under `artifacts/retrieval-ablation-run1.json` and `artifacts/retrieval-ablation-run2.json`; they are not a baseline or deployment claim.

## Required tests and review

- Run metric fixture/property tests, dataset/schema validation, real PostgreSQL retrieval ablations, repeatability/tolerance checks, and JSON/Markdown artifact validation; manually review cases, splits, rationales, and evidence spans.

## Expected file ownership

- Versioned golden manifests/cases, evaluation domain/application code and CLI, metric tests, retrieval ablation configuration, artifact schema/renderers, and evaluation documentation.

## Stop conditions

- Metric definitions, evidence identity, split policy, model identity, or artifact schema needs material change.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.5`, reasoning effort `high`. Do not substitute the model or raise effort; if unavailable, stop before editing. Version action: after all acceptance checks pass, verify `0.5.0` on the latest accepted `main`, apply only the declared minor bump to `0.6.0` through the controlled product-version surfaces in `docs/WORKFLOW.md`, add the `Unreleased` changelog entry, and rerun affected checks; if the predecessor or a gate differs, do not bump, and stop. Work only on EG-009 on branch `feat/eg-009-golden-evaluation`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0006, the artifact schema, and this story. Confirm EG-005 and EG-006 are merged to clean `main`. Author/review the bounded 36-case dataset and implement tested metric definitions, real retrieval ablations, a CLI, and schema-valid JSON/Markdown evidence with full version/environment identity and declared tolerances. Do not set PR thresholds, accept a baseline, call live providers/judges, claim a secret holdout, or add a results UI. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not merge, push, deploy, spend, tag/release, or start another story. Finish with metric definitions, dataset rationale, files, exact commands/artifact paths, limitations, version handoff, and suggested commit message.
