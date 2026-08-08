# Implementation backlog

Each implementation item has one branch, one review boundary, and one manual merge. No feature branch is created by the setup commit. Read [the branch workflow](../WORKFLOW.md) before starting.

EG-001 is the one exception: it creates the initial `main` foundation. After that, create the exact branch shown below only when starting its story.

| Order | Story | Branch | Depends on | Release |
|---|---|---|---|---|
| 0 | [EG-001](EG-001-foundation.md) foundation | setup commit on `main` | R0 | R1 |
| 1 | [EG-002](EG-002-provider-ports.md) provider ports | `feat/eg-002-provider-ports` | EG-001 | R1 |
| 2 | [EG-003](EG-003-postgres-schema.md) PostgreSQL schema | `feat/eg-003-postgres-schema` | EG-002 | R1 |
| 3 | [EG-004](EG-004-governed-corpus.md) governed corpus | `feat/eg-004-governed-corpus` | EG-002, EG-003 | R2 |
| 4 | [EG-005](EG-005-hybrid-retrieval.md) hybrid retrieval | `feat/eg-005-hybrid-retrieval` | EG-004 | R2 |
| 5 | [EG-006](EG-006-grounded-answer.md) grounded answer | `feat/eg-006-grounded-answer` | EG-005 | R2 |
| 6 | [EG-007](EG-007-answer-stream.md) answer stream | `feat/eg-007-answer-stream` | EG-006 | R2 |
| 7 | [EG-008](EG-008-inspection-ui.md) inspection UI | `feat/eg-008-inspection-ui` | EG-007 | R2 |
| 8 | [EG-009](EG-009-golden-evaluation.md) golden evaluation | `feat/eg-009-golden-evaluation` | EG-005, EG-006 | R2 |
| 9 | [EG-010](EG-010-regression-gate.md) regression gate | `feat/eg-010-regression-gate` | EG-009 | R2 |
| 10 | [EG-011](EG-011-results-workbench.md) results workbench | `feat/eg-011-results-workbench` | EG-008, EG-009 | R3 |
| 11 | [EG-015](EG-015-governed-live-eval.md) governed live evaluation | `feat/eg-015-governed-live-eval` | EG-006, EG-009 | R3 |
| 12a | [EG-013A](EG-013A-public-security.md) public security | `feat/eg-013a-public-security` | EG-008, EG-010, EG-011 | R3 |
| 12b | [EG-013B](EG-013B-accessibility-safety.md) accessibility/content safety | `feat/eg-013b-accessibility-safety` | EG-008, EG-011 | R3 |
| 12c | [EG-013C](EG-013C-observability-cost.md) observability/cost | `feat/eg-013c-observability-cost` | EG-010, EG-011 | R3 |
| 12d | [EG-013D](EG-013D-operations-sbom.md) operations/SBOM | `feat/eg-013d-operations-sbom` | EG-013A, EG-013B, EG-013C, EG-015 | R3 |
| 13 | [EG-014](EG-014-release-evidence.md) release evidence | `docs/eg-014-release-evidence` | EG-013D, EG-015 | R3 |
| After R3 | [EG-012](EG-012-mcp-adapter.md) MCP adapter | `feat/eg-012-mcp-adapter` | EG-014 | R4 |
| Optional | [EG-016](EG-016-public-deployment.md) public deployment | `feat/eg-016-public-deployment` | EG-014 and explicit approval | R5 |

EG-003 starts only after EG-002 verifies and merges the reference embedding identity and 384-dimensional schema decision. Every story starts only after every listed dependency is on `main` and is still reviewed and merged separately.

Every story file contains the exact brief to give a coding agent and requires the repository-wide `AGENTS.md` rules. Together they forbid merging, pushing, and branch deletion. External calls, spending, and deployment are also forbidden unless EG-015 or EG-016 reaches its explicit decision gate and the repository owner authorizes the named action. The repository owner reviews the diff, asks for an explanation, runs checks, and performs the merge manually.
