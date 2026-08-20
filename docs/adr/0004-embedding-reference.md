# ADR-0004: Local 384-dimensional reference embedding

- Status: Accepted; identity verified, runtime execution gated
- Date: 2026-08-08
- Verified: 2026-08-20
- Story: EG-002

## Context

Pull-request retrieval evidence must not require a paid secret. Schema width and index identity must remain reproducible. FastEmbed's public model name is an alias: its runtime artifact is not the ONNX file in the logical BAAI repository, and the convenience download API does not pin a Hugging Face revision.

## Decision

Use FastEmbed `0.8.0` with ONNX Runtime CPU `1.29.0` for the local reference embedding and retain the literal `vector(384)` schema.

The immutable identity has two provenance chains, both recorded in the [reference manifest](../../contracts/manifests/reference-embedding.json):

| Purpose | Repository | Revision | License | Artifact |
|---|---|---|---|---|
| Logical model | `BAAI/bge-small-en-v1.5` | `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` | MIT | `onnx/model.onnx`, 133,093,490 bytes, SHA-256 `828e1496d7fabb79cfa4dcd84fa38625c0d3d21da474a00f08db0f559940cf35` |
| FastEmbed runtime | `qdrant/bge-small-en-v1.5-onnx-q` | `52398278842ec682c6f32300af41344b1c0b0bb2` | Apache-2.0 | `model_optimized.onnx`, 66,465,124 bytes, SHA-256 `51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431` |

A future real adapter must provision the exact runtime revision, verify every manifest-listed file at application level, and only then construct FastEmbed with a verified `specific_model_path`, local-only loading, an explicit application cache, and `CPUExecutionProvider`. It must fail closed on a missing or mismatched file. Passing only `model_name="BAAI/bge-small-en-v1.5"` is not an immutable runtime selection.

FastEmbed 0.8.0 applies no textual prefix in its query or passage methods for this model. Query and document inputs therefore use the same raw text transform, with empty prefixes. Adding the older BGE query instruction would create a different embedding space and requires a new decision and evaluation.

Cross-platform numeric tolerance is explicitly unmeasured, not guessed. EG-002 makes no bit-for-bit or cross-platform repeatability claim. The real adapter story must record reference vectors on declared platforms, and EG-009 ratifies a comparison tolerance before the regression gate can rely on it. EG-003 may rely only on the verified 384-dimensional identity.

## Consequences

- Deterministic fixture vectors remain labeled mechanics evidence and cannot replace or validate the real embedding.
- No FastEmbed dependency, model download, or real adapter is added by EG-002.
- A dimension or identity change creates a new index version and a reviewed migration/reset path.
- CI may cache a pre-provisioned public snapshot, but runtime loading must follow the manifest verifier rather than a mutable convenience download.

## Verification

Contract tests pin both repository identities, licenses, revisions, artifact sizes/digests, package versions, CPU provider, empty-prefix policy, and the unmeasured tolerance state. Snapshot tests cover both SHA-256 and Hugging Face Git-blob verification and prove a digest mismatch fails closed before runtime construction.

Primary evidence: [BAAI repository metadata](https://huggingface.co/api/models/BAAI/bge-small-en-v1.5?blobs=true), [Qdrant runtime metadata](https://huggingface.co/api/models/qdrant/bge-small-en-v1.5-onnx-q?blobs=true), [FastEmbed 0.8.0 source](https://github.com/qdrant/fastembed/tree/6fa442b9603cd197c4b8cf19f072b3b9bbaac9b0), [FastEmbed package metadata](https://pypi.org/project/fastembed/0.8.0/), and [ONNX Runtime package metadata](https://pypi.org/project/onnxruntime/1.29.0/).
