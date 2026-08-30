# EvalGate

EvalGate helps AI application teams detect retrieval, grounding, and citation regressions before release.

The repository currently contains the approved production blueprint, reproducible engineering foundation, provider-neutral application boundary, governed corpus ingestion, explainable hybrid retrieval, and a framework-free grounded-answer core. HTTP answer streaming and evaluation capabilities remain planned; the status table below is the source of truth.

| Capability | Status |
|---|---|
| Production blueprint | Approved |
| Repository/tooling foundation | Static/code and local PostgreSQL checks pass; remote CI evidence pending |
| Provider ports and reference identity | Implemented and locally verified with fixtures and the pinned local reference runtime; remote CI pending |
| PostgreSQL schema and migration readiness | Implemented, merged, and locally verified; remote CI pending |
| Corpus and ingestion | Implemented, merged, and locally verified; remote CI pending |
| Hybrid retrieval | Implemented, merged, and locally verified; remote CI pending |
| Grounded-answer core and validated citations | Implemented and locally verified on the EG-006 review branch; HTTP exposure remains planned for EG-007 |
| Evaluation gate and results UI | Planned |
| MCP adapter | Deferred until the core release |
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

The transport-independent answer flow and its citation trust boundary are documented in
[docs/grounded-answer.md](docs/grounded-answer.md). EG-006 exposes no answer HTTP endpoint.

Copy `.env.example` to `.env` only when overriding local defaults. Provider modes are explicit and default locally to labeled deterministic fixtures. Reference mode requires a pre-provisioned local snapshot that must pass the manifest verifier before runtime construction; live generation remains unavailable, and no external provider call exists.

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
docs/runbooks/      Operational procedures
scripts/            Reproducible developer and publication checks
```

## License

Code is available under the MIT License. The original fictional Northstar Operations Handbook
files under `data/corpus/documents/` are dedicated under CC0-1.0; see the included legal text at
`data/corpus/CC0-1.0.txt` and `NOTICE.md`. This dedication covers authored corpus content only,
not code, dependencies, or the embedding model files.
