# ADR-0007: Original governed operations corpus

- Status: Accepted
- Date: 2026-08-08
- Story: EG-004

## Context

External or scraped corpora create reproducibility, attribution, coherence, privacy, and availability risk.

## Decision

Author a fictional Northstar Operations Handbook with 15-25 technical documents, an immutable manifest, stable source/evidence identity, and intentional hard cases. The full approved CC0-1.0 legal text is bundled before the corpus. CC0-1.0 applies only to the original authored documents under `data/corpus/documents/**`; it does not license application code, dependencies, embedding-model artifacts, or external model licenses.

The initial index policy is versioned in `contracts/manifests/northstar-index-policy-v1.json`. Its identity is SHA-256 over canonical JSON (UTF-8, sorted keys, compact separators, and one terminal LF), so insignificant JSON formatting does not create a new index identity. Source and CC0 legal-text hashes are SHA-256 over strict-UTF-8 content normalized to NFC and LF with exactly one terminal LF. Offsets are Python Unicode-code-point indices into that normalized source and reconstruct chunk content exactly. Each H2 creates one chunk through the next H2, H3 remains within that parent, and section keys combine the source key with a unique ASCII slug. The reviewed local FastEmbed tokenizer determines token count and limits chunks to 512 tokens; lexical vectors use `pg_catalog.simple`.

## Consequences

Corpus and golden authoring require substantive review, but no external fetch or hidden dependency is needed.

## Verification

License/provenance/schema/hash checks, personal/proprietary-data review, and idempotent ingestion.
