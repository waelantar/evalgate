# EG-009: Golden dataset and retrieval evaluation

- Status: Planned
- Branch: `feat/eg-009-golden-evaluation`
- Depends on: EG-005 and EG-006 merged to `main`
- Release: R2
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
- [ ] Real PostgreSQL and pinned embedding evaluation is repeatable within declared tolerance.
- [ ] Artifacts validate against schema and record every required version/environment field.
- [ ] Splits and case edits have review/provenance; six calibration cases are not treated as sufficient judge authorization.

## Required tests and review

- Run metric fixture/property tests, dataset/schema validation, real PostgreSQL retrieval ablations, repeatability/tolerance checks, and JSON/Markdown artifact validation; manually review cases, splits, rationales, and evidence spans.

## Expected file ownership

- Versioned golden manifests/cases, evaluation domain/application code and CLI, metric tests, retrieval ablation configuration, artifact schema/renderers, and evaluation documentation.

## Stop conditions

- Metric definitions, evidence identity, split policy, model identity, or artifact schema needs material change.

## Copy-paste coding-agent brief

> Work only on EG-009 on branch `feat/eg-009-golden-evaluation`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0006, the artifact schema, and this story. Confirm EG-005 and EG-006 are merged to clean `main`. Author/review the bounded 36-case dataset and implement tested metric definitions, real retrieval ablations, a CLI, and schema-valid JSON/Markdown evidence with full version/environment identity and declared tolerances. Do not set PR thresholds, accept a baseline, call live providers/judges, claim a secret holdout, or add a results UI. Do not merge or push. Finish with metric definitions, dataset rationale, files, exact commands/artifact paths, limitations, and suggested commit message.
