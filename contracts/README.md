# Contracts

Contracts are reviewed before implementation that depends on them. Their status is explicit:

| Contract | Status | Owning story |
|---|---|---|
| [Foundation health OpenAPI](openapi/foundation.yaml) | Implemented in setup | EG-001 |
| [Answer stream wire contract](events/answer-stream.md) | Draft; not implemented | EG-007 |
| [Corpus manifest schema](manifests/corpus.schema.json) | Draft; not implemented | EG-004 |
| [Evaluation artifact schema](evaluation/artifact.schema.json) | Draft; not implemented | EG-009 |
| Search/ask OpenAPI | Not created | EG-005 to EG-007 |
| MCP tool schemas | Not created | EG-012 |

A draft is a planning constraint, not proof of a running capability. The owning story may refine a draft through an ADR/contract review before code lands.
