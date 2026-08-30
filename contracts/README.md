# Contracts

Contracts are reviewed before implementation that depends on them. Their status is explicit:

| Contract | Status | Owning story |
|---|---|---|
| [Health/search OpenAPI](openapi/foundation.yaml) | Health and search implemented, merged, and locally verified | EG-001, EG-005 |
| [Reference embedding manifest](manifests/reference-embedding.json) | Accepted; verifier and explicit local/CI snapshot provisioning implemented | EG-002 to EG-004 |
| [Hybrid retrieval policy](retrieval/hybrid-rrf-v1.json) | Accepted; implemented, merged, and locally verified | EG-005 |
| [Grounded-answer prompt policy](prompts/grounded-answer-v1.json) | Accepted; implemented and locally verified on the EG-006 review branch | EG-006 |
| [Answer stream wire contract](events/answer-stream.md) | Draft; not implemented | EG-007 |
| [Corpus manifest schema](manifests/corpus.schema.json) | Implemented and merged | EG-004 |
| [Evaluation artifact schema](evaluation/artifact.schema.json) | Draft; not implemented | EG-009 |
| MCP tool schemas | Not created | EG-012 |

A draft is a planning constraint, not proof of a running capability. The owning story may refine a draft through an ADR/contract review before code lands.
