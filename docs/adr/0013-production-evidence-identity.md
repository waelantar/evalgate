# ADR-0013: Bind reviewed evidence IDs to production chunking

- Status: Accepted
- Date: 2026-09-21
- Owners: architecture and evaluation governance
- Story: EG-020
- Supersedes: The dataset-identity assumption in ADR-0012; source and chunking decisions remain unchanged

## Context

EG-020 proved that Northstar contained one transcribed UUID and that the Kubernetes dataset evidence IDs were authored from the 77-chunk whitespace test tokenizer. Production uses the verified reference tokenizer and produces 75 chunks. The old IDs therefore cannot all identify production evidence.

## Decision drivers

- Close the release-blocking retrieval gate with the smallest reproducible correction.
- Keep source text, questions, labels, retrieval policy, and baseline thresholds unchanged.
- Preserve historical paid-run artifacts rather than rewriting evidence.

## Considered options

1. Keep invalid dataset IDs and leave the release blocked.
2. Change production chunking to reproduce a test double.
3. Patch dataset evidence mappings to deterministic production UUIDs and retain historical artifacts.

## Decision

Use option 3. Patch `golden-v1` and `kubernetes-debug-v1` dataset versions from `1.0.0` to `1.0.1`, changing only invalid `relevant_evidence_ids`. UUIDs are derived from the accepted index, document, production ordinal, and content hash. Existing live artifacts and review records retain their original dataset checksums and remain historical EG-018 evidence; they are not current-dataset acceptance evidence.

## Consequences

### Positive

- Every reviewed evidence reference resolves against fresh production chunks.
- The 161-chunk Northstar and 75-chunk Kubernetes contracts remain unchanged.
- No provider rerun, source edit, ranking change, or baseline relaxation is required.

### Negative and residual risk

- Historical EG-018 live artifacts remain bound to dataset `1.0.0` and cannot be imported as current `1.0.1` results.
- A future live comparison must run against `1.0.1` before making current model-quality claims.

## Verification

The focused EG-020 test resolves every reviewed ID for both corpora. Fresh PostgreSQL ingestion, the 36-case real-reference retrieval gate, and repository checks must pass without baseline changes.

## Revisit trigger

Revisit only if production tokenization, chunk content, or evidence UUID derivation changes.
