# EG-018: Governed real-world RAG showcase and multi-model evidence

- Status: Merged to `main` at `0.11.0`; EG-014 later found a Northstar identity regression introduced by the generalized chunk ordinal logic
- Branch: `feat/eg-018-real-world-showcase`
- Depends on: EG-017 merged to `main`
- Release: R3
- Version action: Minor `0.10.0 -> 0.11.0`
- Codex profile: `gpt-5.5` with `high` reasoning
- Blueprint requirements: G-04/05/10, FR-06/07/08/14, NFR-03/05/11

## Outcome

A reviewer can open one truthful, reproducible real-world documentation showcase, see how EvalGate
builds and inspects its evidence, and compare governed runs from several models on the same cases
without mistaking the result for a public benchmark, production traffic, or a universal model rank.

## Decision gates before implementation

1. Record and approve an ADR for exactly one real-world source snapshot, its license/attribution,
   selected paths, transformation policy, trademarks, repository footprint, and update policy.
   Preferred candidate: a bounded troubleshooting/operations subset of `kubernetes/website` at one
   immutable commit under CC BY 4.0. Do not fetch or commit content before owner confirmation.
2. Reverify every OpenRouter candidate's current availability, price, structured-output support,
   endpoints/providers, retention/ZDR behavior, and parameter compatibility from primary sources.
3. Obtain new explicit owner approval naming the exact model slugs, corpus text allowed to leave the
   machine, provider-routing/privacy policy, repetitions, maximum spend, and lower stop limit. The
   EG-015 approval and budget do not carry over.

## Scope

- Vendor a small, coherent real-world documentation snapshot only after the source ADR is accepted.
  Store upstream commit, paths, original URLs, authorship attribution, license text/link, normalized
  content hashes, transformations, and exclusions. No runtime crawling, mutable URL fetch, broad
  mirror, images, generated API reference, personal data, or trademark/endorsement implication.
- Create a separately versioned, human-reviewed demonstration dataset derived from realistic
  questions answerable by the selected documentation. Include answerable, cross-document,
  terminology, outdated-assumption, and unanswerable cases with reviewed evidence labels. State
  that questions/labels are EvalGate-authored and that this is not production-user traffic.
- Ingest through the existing governed pipeline with a distinct corpus/index identity, idempotency,
  rollback, and PostgreSQL/reference-embedding evidence. Do not change the Northstar baseline or
  merge the real-world set into the PR regression threshold without a separate baseline decision.
- Extend the governed OpenRouter evaluation allowlist only for approved models that satisfy the
  same prompt/output/privacy contract. Reverify the exact candidate slugs
  `deepseek/deepseek-v4-flash`, `deepseek/deepseek-v4-flash-0731`, `z-ai/glm-5.3-flash`,
  `tencent/hy3`, and `xiaomi/mimo-v2.5` before selecting human-facing names. If MiMo still lacks
  structured `response_format`, exclude it with a visible reason or stop for a separately reviewed
  adapter contract; never silently parse a different free-form output shape.
- Execute the same dataset, corpus/index, prompt, evidence budget, output schema, generation
  settings, and repetitions for every included model. Disable provider fallback; record routed
  provider/model revision, usage, cost, latency/status, and failure counts. Missing/failed cases are
  failures or unavailable evidence, never zero-cost successes.
- Make human review primary. Randomize or blind model order for pairwise/case review where
  practical. If an LLM judge is used, apply one declared judge policy consistently, keep it
  advisory, disclose self/family bias, and report human agreement and missing judge results.
- Produce schema-valid JSON plus readable Markdown evidence and a read-only UI showcase using the
  EG-017 product shell. Show a concise comparison summary, cost/latency/availability trade-offs,
  regressions and case-level outputs/evidence; use human model names first and technical slugs in
  details. Do not put a provider key or live-run button in the browser.
- Add a guided “How this example works” path covering source snapshot, chunk/index identity,
  question, retrieved evidence, model output/citations, scoring/review, comparison, and limitations.

## Non-goals

- A leaderboard, claim of best model, public benchmark, production telemetry, general dataset
  marketplace, arbitrary URL/file ingestion, Kubernetes deployment, live browser model picker,
  automatic baseline replacement, uncalibrated judge gate, provider fallback, public deployment,
  or more than one real-world source corpus.

## Implemented evidence

- Approved source gate: 11 Kubernetes debug-cluster Markdown files pinned at commit `aa4e9e6dee49106155072a44ef997b91722243ec` with CC BY 4.0 attribution and no-endorsement disclosure.
- Reviewed dataset/index: 18 cases, 75 evidence chunks, immutable manifest/hash checks, idempotent ingestion, and rollback coverage.
- Repaired comparable live set: base DeepSeek 3/18, DeepSeek 0731 4/18, and GLM 3/18; total artifact-reported EG-018 spend USD 0.019973359 under the USD 0.80 stop.
- Root cause of the earlier zero-cost failures: stale request `max_price` ceilings below every selected provider route. Corrected ceilings retain per-request, per-run, and global budget controls.
- Additional diagnostics: Hy3 timed out/unavailable; MiMo produced malformed output/unavailable. Neither was promoted into the comparable quality table.
- Read-only Showcase reports provenance, status distribution, costs, exclusions, limitations, and artifact hashes. No browser secret, live-run control, provider fallback, deployment, push, or merge exists.
## Acceptance evidence

- [ ] The accepted source ADR and manifest pin exact upstream commit/paths/URLs, CC BY 4.0
      attribution/license, normalized hashes, transformations, exclusions, and no-endorsement text;
      clean-checkout validation fails on any byte drift.
- [ ] The bounded demonstration dataset is human-reviewed, versioned, schema-valid, traceable to
      evidence, and labeled accurately as curated real-world showcase cases—not production traffic
      or an external benchmark.
- [ ] Repeated ingestion produces the same corpus/index identity and an injected failure leaves no
      partial corpus/index state.
- [ ] Before any paid call, preflight tests prove exact model allowlist, no fallback, ZDR/data
      collection denial request, parameter compatibility, redaction, per-model caps, global budget,
      and stop behavior; explicit approval is recorded.
- [ ] At least three approved compatible models complete the same bounded suite with reviewed
      provider/model/prompt/corpus/index/dataset/repetition/usage/cost/latency/status identity. Every
      excluded candidate has an evidence-backed reason.
- [ ] Human review and any advisory judge results are separately reported; incomplete, malformed,
      timeout, unavailable, and unsupported-output results remain visible in aggregates and cases.
- [ ] The read-only UI explains the full under-the-hood flow and compares only like-for-like runs,
      using names first and technical identities only in details; responsive/accessibility/error
      tests pass with no browser secret or execution endpoint.
- [ ] The existing Northstar regression baseline remains byte-identical and still passes. Full
      checks, real PostgreSQL/reference retrieval, artifact validation, cost reconciliation, and
      publication/privacy review pass before and after the controlled `0.11.0` bump.

## Required tests and review

- Manifest/license/hash and path allowlist tests; idempotent ingestion plus transactional rollback.
- Golden-case schema/review checks, retrieval metrics/ablations, and unchanged Northstar baseline.
- Fake-provider contract tests for every approved model capability profile, privacy/routing fields,
  no fallback, timeout/malformed/error/cap paths, and artifact redaction before external calls.
- Approved bounded live repetitions, artifact-schema validation, human review, judge-agreement
  analysis if used, total-cost reconciliation, and kill-criteria verification.
- Component/Playwright flows for showcase overview, comparison, failure filtering, case evidence,
  technical disclosure, responsive layout, keyboard/focus/axe, and unavailable artifact states.

## Expected file ownership

- A proposed/accepted source-and-comparison ADR; one real-world manifest/license/attribution bundle
  and bounded source files; one reviewed demonstration dataset; focused ingestion/evaluation/model
  allowlist code and tests; artifact schema/evidence docs; EG-017 showcase UI/API projections;
  README/blueprint/changelog and controlled version surfaces after pre-bump verification.

## Stop conditions

- Source license/attribution/trademark scope is unclear, selected content contains personal or
  unsuitable data, content cannot be pinned, or repository size exceeds the reviewed bound.
- Fewer than three candidates support one honest comparable contract, ZDR/data-collection denial
  cannot be enforced, no explicit corpus-egress/spend approval exists, or cost approaches the stop
  limit. Do not weaken the contract, add free-form parsing, or reuse EG-015 authority.
- A positive quality claim would depend on unreviewed labels, an uncalibrated judge, missing cases,
  cross-dataset comparisons, or a silent provider/model substitution.

## Agent and scope control

Use one implementation agent. Do not create subagents: source provenance, model policy, artifacts,
and product claims require one accountable evidence chain and serialized paid calls.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.5`, reasoning effort `high`. Do not substitute the model or raise effort; stop if unavailable. Version action: after all implementation and approved live-evidence gates pass, verify the latest accepted `main` is exactly `0.10.0`, apply only the minor bump to `0.11.0` through `docs/WORKFLOW.md`, and rerun all version-bound evidence; otherwise retain `0.10.0`. Work only on EG-018 on `feat/eg-018-real-world-showcase`. Read `AGENTS.md`, complete `BLUEPRINT.md`, `docs/product/UX-RESEARCH.md`, ADR-0004/0006/0007/0011, corpus/evaluation/live-artifact contracts, EG-004/009/010/015/017 evidence, and this story. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. First stop for owner approval of one exact pinned real-world source snapshot; the preferred candidate is a bounded Kubernetes troubleshooting/operations documentation subset with CC BY 4.0 attribution. Then implement its immutable manifest, reviewed demonstration cases, idempotent ingestion, unchanged-Northstar proof, and read-only guided showcase. Before any OpenRouter call, reverify the five named candidate pages and stop for a new explicit approval naming included slugs, permitted corpus egress, ZDR/data-collection denial/no-fallback routing, repetitions, hard budget, and lower stop limit; EG-015 approval does not apply. Compare at least three compatible approved models using identical corpus/index/dataset/prompt/output/settings/repetitions, human review first, and an advisory disclosed judge only if approved. If MiMo or another candidate lacks the shared structured-output contract, exclude it visibly or stop for a separate contract—never add silent free-form parsing. Record provider identity, usage, cost, latency/status, failures, limitations, and case evidence without prompts, raw corpus duplication, secrets, or a “best model” claim. Add no crawler, uploads, marketplace, browser key/run button, fallback, automatic baseline update, unrelated refactor, speculative cases, or deployment. Run provenance/hash/license, ingestion rollback/idempotency, unchanged baseline, fake-provider cap/redaction/error, approved live, artifact, UI/E2E/accessibility, publication, and full repository checks. Do not merge, push, deploy, tag/release, start EG-014 finalization, or create subagents. Finish with source/model decisions, exact external calls and spend, data/evaluation flow, files, tests, human/judge evidence, limitations, version handoff, and suggested commit message.
