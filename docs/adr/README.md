# Architecture decision records

ADRs capture decisions that are expensive or unsafe to change silently. The blueprint is the governing summary; an ADR records context, alternatives, consequences, and the story that verifies the choice.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-application-boundaries.md) | Framework-independent application core | Accepted |
| [0002](0002-postgresql-only.md) | PostgreSQL/pgvector in every environment | Accepted |
| [0003](0003-hybrid-retrieval.md) | Exact lexical/vector retrieval fused with RRF | Accepted |
| [0004](0004-embedding-reference.md) | Local 384d BGE reference embedding | Accepted; identity verified, runtime execution gated |
| [0005](0005-post-fetch-sse.md) | POST plus fetch-consumed SSE framing | Accepted |
| [0006](0006-evaluation-layers.md) | Separate fixture, retrieval, and live assurance | Accepted |
| [0007](0007-governed-corpus.md) | Original governed operations corpus | Accepted with license-text gate |
| [0008](0008-mcp-stdio.md) | Separate local MCP stdio adapter after core release | Accepted |
| [0009](0009-public-mode.md) | Read-only bounded public posture | Accepted with deployment gate |
| [0010](0010-defer-external-services.md) | Defer provider and host selection | Accepted |

Use [0000-template.md](0000-template.md) for a new decision. Never rewrite an accepted ADR to hide history; supersede it with a new ADR.
