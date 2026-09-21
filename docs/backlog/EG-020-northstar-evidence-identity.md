# EG-020: Restore Northstar evidence identity and retrieval gate

- Status: Implemented and locally verified; awaiting owner review, merge, and exact-commit CI
- Branch: `fix/eg-020-northstar-evidence-identity`
- Depends on: EG-019 merged to `main`
- Release: R3
- Version action: Patch `0.12.0 -> 0.12.1`
- Codex profile: `gpt-5.6-sol` with `medium` reasoning
- Blueprint requirements: G-04/05/10, FR-06/14, NFR-03/05/11

## Outcome

The original Northstar corpus again produces deterministic evidence UUIDs for the 36-case golden
dataset. Kubernetes production chunks and historical artifacts remain unchanged, while ADR-0013
corrects invalid reviewed mappings to the accepted 75-chunk identity. A fresh database passes the
real reference-embedding retrieval regression gate.

## Problem statement

EG-018 generalized corpus chunking and changed `CorpusChunk.ordinal` from a per-document ordinal
to `len(chunks)`, a corpus-global ordinal. Evidence UUIDs include document ID, ordinal, and content
hash, so almost every Northstar UUID changed even though ADR-0012 explicitly required Northstar's
policy and identity to remain unchanged. The exact merged-main CI run
`https://github.com/waelantar/evalgate/actions/runs/35444229759` and an isolated local reproduction
both report precision@5 `0.005556`, recall@5/MRR/nDCG@5/source coverage `0.027778` (nDCG rounded),
instead of the reviewed baseline range.

## Scope

- Restore the original Northstar per-document ordinal and deterministic evidence UUID contract.
- Preserve Kubernetes debug-cluster chunk content, section keys, ordinals, live artifacts, and
  review records; correct only invalid reviewed dataset evidence mappings under ADR-0013.
- Add a focused regression test that proves every Northstar golden relevant-evidence UUID exists
  in the freshly chunked corpus and every Kubernetes reviewed relevant-evidence UUID remains valid.
- Apply the owner-approved ADR-0013 evidence-ID-only dataset corrections (1.0.1); preserve
  questions, labels, source/chunk content, baseline thresholds, and historical live artifacts.
- Run fresh PostgreSQL ingestion plus the 36-case reference retrieval gate before and after the
  controlled patch bump.

## Non-goals

- Changing questions, labels, source/chunk content, the retrieval baseline, chunking policy,
  re-running paid models, changing retrieval ranking, fixing dependency advisories, release
  finalization, deployment, or unrelated refactoring.

## Acceptance evidence

- [x] A focused test fails on merged `0.12.0` because reviewed Northstar UUIDs are missing.
- [x] Northstar produces 161 chunks and all non-empty `golden-v1.json` evidence UUIDs resolve.
- [x] Kubernetes produces 75 chunks and all non-empty `kubernetes-debug-v1.json` evidence UUIDs
      resolve without changing source/chunk content, historical artifacts, or review records.
- [x] Fresh-database ingestion remains transactional and idempotent for both corpora.
- [x] The real reference-embedding retrieval artifact passes
      `scripts/check_retrieval_baseline.py` without modifying the baseline.
- [x] `scripts/check.ps1` and all 16 PostgreSQL/reference integration tests pass before applying
      the controlled `0.12.1` version and all version-bound checks pass afterward.

## Expected file ownership

- `apps/api/src/evalgate/adapters/bundled_corpus.py`
- Focused corpus/ingestion regression tests only
- Product-version surfaces listed in `docs/WORKFLOW.md`
- `CHANGELOG.md` and this story's evidence

## Stop conditions

- The fix would change source/chunk content, the retrieval baseline, historical live
  artifacts/reviews,
  questions/labels, ranking, or any governed field beyond the ADR-0013 evidence mappings.
- The retrieval gate still fails after reviewed evidence identity is restored.

## Copy-paste coding-agent brief

> Execution profile (configure before starting): `gpt-5.6-sol`, reasoning effort `medium`. Do not substitute the model or raise effort; stop if unavailable. Version action: after every implementation and retrieval gate passes, apply only the patch bump `0.12.0 -> 0.12.1` through the controlled product-version surfaces and rerun version-bound checks. Work only on EG-020 on branch
> `fix/eg-020-northstar-evidence-identity` from clean merged `main` at exactly `0.12.0`. Read
> `AGENTS.md`, ADR-0003, ADR-0006, ADR-0007, ADR-0012, EG-018, EG-019, the EG-014 readiness
> finding, and this story. First add a focused failing test proving that all reviewed Northstar and
> Kubernetes evidence UUIDs resolve from freshly chunked corpora. Restore Northstar's original
> per-document ordinal semantics while preserving Kubernetes production chunks and historical
> artifacts. Apply only the owner-approved ADR-0013 evidence-ID mapping corrections. Implement only cases explicitly required by this story, accepted contracts/ADRs, or an observed failing test. Do not invent speculative edge cases, future-proof abstractions, new dependencies/frameworks, opportunistic refactors, later-story work, or silent contract/architecture decisions; stop and report instead. Do not edit questions, labels, the retrieval baseline, live artifacts/reviews, chunk text,
> policies, ranking, or unrelated code. Run focused tests, `scripts/check.ps1`, all 16 integration
> tests, and a fresh-database real reference retrieval gate. Only after all pass, apply the patch
> bump `0.12.0 -> 0.12.1` through the controlled surfaces and rerun version-bound checks. Do not
> merge, push, deploy, spend, call a provider, tag/release, fix dependency advisories, or start
> EG-014. Stop on any unapproved governed-artifact change or remaining baseline failure. Finish with exact
> UUID invariants, files, commands/results, version evidence, limitations, and suggested commit.
