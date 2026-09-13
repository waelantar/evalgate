# EvalGate

EvalGate helps AI application teams detect retrieval, grounding, and citation regressions before release.

The repository currently contains the approved production blueprint, reproducible engineering foundation, provider-neutral application boundary, governed corpus ingestion, explainable hybrid retrieval, a grounded-answer core, versioned answer streaming, deterministic evaluation gates, and local read-only answer and evaluation inspection workbenches. The status table below is the source of truth.

| Capability | Status |
|---|---|
| Production blueprint | Approved |
| Repository/tooling foundation | Implemented and locally verified from a clean checkout; remote CI run still needs release-record linkage |
| Provider ports and reference identity | Implemented and locally verified with fixtures and the pinned local reference runtime |
| PostgreSQL schema and migration readiness | Implemented and locally verified with migrations, real integration tests, and readiness checks |
| Corpus, ingestion, and hybrid retrieval | Implemented and locally verified; fresh 36-case reference retrieval evidence passes the immutable reviewed baseline |
| Grounded answers, SSE, and inspection UI | Implemented and locally verified with contracts, browser/E2E checks, and server-derived citations; no public live provider claim |
| Evaluation gate and results UI | Implemented and locally verified; governed live-generation evidence is protected/manual and limitation-heavy, not a quality-success claim |
| Public-mode application security and operations | Implemented application boundary, browser-safety automation, redacted telemetry, controls, local image, and runbooks; no hosting or deployment authorization |
| R3 release | Blocked at `0.9.0`; see [release readiness](docs/release/READINESS.md) for the required scanner, manual accessibility, and remote-CI evidence |
| MCP adapter | Deferred until R3 is accepted |
| Public deployment | Not selected or deployed |

Start with [BLUEPRINT.md](BLUEPRINT.md). The detailed implementation queue is in [docs/backlog](docs/backlog/README.md), and architectural changes are recorded in [docs/adr](docs/adr/README.md).

Future work follows the [one-story branch and manual-merge workflow](docs/WORKFLOW.md). The coding agent prepares and explains a story branch; the repository owner reviews and merges it manually.

## Prerequisites

- Git
- Docker with Compose v2
- Python 3.13.15 and [uv 0.12.3](https://docs.astral.sh/uv/)
- Node.js 24.19.0 LTS

## Local setup

PowerShell:

```powershell
./scripts/bootstrap.ps1
./scripts/check.ps1
```

POSIX shell:

```sh
./scripts/bootstrap.sh
./scripts/check.sh
```

Then run the services in separate terminals:

```powershell
uv run --python 3.13.15 --project apps/api --locked evalgate-api
npm --prefix apps/web run dev
```

- Web: <http://127.0.0.1:5173>
- API documentation: <http://127.0.0.1:8000/docs>
- Liveness: <http://127.0.0.1:8000/health/live>
- Readiness: <http://127.0.0.1:8000/health/ready>

The bounded search endpoint and content-free ablation workflow are documented in
[docs/retrieval.md](docs/retrieval.md). Queries are accepted only in POST bodies or through
standard input; they are not placed in URLs or access logs.

The answer flow and citation trust boundary are documented in
[docs/grounded-answer.md](docs/grounded-answer.md). The frozen POST/fetch/SSE framing, ordering,
retry, heartbeat, backpressure, and cancellation rules are documented in the
[answer-stream contract](contracts/events/answer-stream.md).

The reviewed-artifact import boundary, bounded result storage, read-only API, and results UI are
documented in [evaluation governance](docs/evaluation/README.md). Evaluation imports are local-only;
CI and public mode cannot invoke them.

Copy `.env.example` to `.env` only when overriding local defaults. Provider modes are explicit and
default locally to labeled deterministic fixtures. Reference mode requires a pre-provisioned local
snapshot that must pass the manifest verifier before runtime construction. Governed live generation
is available only through the EG-015 live-evaluation command or protected manual workflow after an
approved provider, key, retention posture, and budget are configured.

The application-side public-mode boundary and its required configuration are documented in
[public-mode security](docs/security/public-mode.md). This hardening does not enable public live
generation or authorize deployment; EG-013C/D, EG-014, and optional EG-016 remain required.

Bootstrap waits for the digest-pinned PostgreSQL 18/pgvector service and applies the forward-only
empty-schema migration. Database reset is a separately confirmed, loopback-only recovery command;
see [the database migration guide](apps/api/migrations/README.md).

## Repository map

```text
apps/api/           Python application core and API adapters
apps/web/           React foundation; inspection interface begins in EG-008
contracts/          Versioned machine-readable contracts
data/               Governed corpus, golden set, and manifests
docs/adr/           Architecture decision records
docs/backlog/       Story contracts and implementation briefs
docs/security/      Public-mode policy and threat-model evidence
docs/runbooks/      Operational procedures
scripts/            Reproducible developer and publication checks
```

## License

Code is available under the MIT License. The original fictional Northstar Operations Handbook
files under `data/corpus/documents/` are dedicated under CC0-1.0; see the included legal text at
`data/corpus/CC0-1.0.txt` and `NOTICE.md`. This dedication covers authored corpus content only,
not code, dependencies, or the embedding model files.
